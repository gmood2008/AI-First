"""
Undo Manager - Time machine for operation rollback.

This module provides the ability to undo operations by maintaining
a stack of reversible actions with backup data.
"""

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..types import UndoRecord


class UndoManager:
    """
    Manages operation history and provides rollback capabilities.
    
    This is the "time machine" that allows users to undo operations
    by maintaining backups and undo handlers.
    """
    
    def __init__(self, backup_dir: Path):
        """
        Initialize undo manager.
        
        Args:
            backup_dir: Directory for storing backups
        """
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.stack: List[UndoRecord] = []
        self._max_stack_size = 100  # Prevent unlimited growth
    
    def record(
        self,
        capability_id: str,
        params: Dict[str, Any],
        undo_handler: Optional[Callable[[], None]] = None,
        backup_data: Optional[Dict[str, Any]] = None,
        description: str = "",
    ) -> None:
        """
        Record an operation for potential undo.
        
        Args:
            capability_id: ID of the capability that was executed
            params: Parameters used for the operation
            undo_handler: Function to call for undo (optional)
            backup_data: Data needed for rollback (optional)
            description: Human-readable description
        """
        record = UndoRecord(
            operation_id=f"{capability_id}_{datetime.now().timestamp()}",
            capability_id=capability_id,
            timestamp=datetime.now(),
            params=params,
            undo_function=undo_handler if undo_handler else lambda: None,
            undo_args=backup_data or {},
            description=description or f"Executed {capability_id}",
        )
        
        self.stack.append(record)
        
        # Limit stack size
        if len(self.stack) > self._max_stack_size:
            # Remove oldest record
            old_record = self.stack.pop(0)
            self._cleanup_backup(old_record)
        
        print(f"📝 Recorded undo: {capability_id} (stack size: {len(self.stack)})", file=sys.stderr)
    
    def push(self, record: UndoRecord) -> None:
        """
        Push an UndoRecord onto the stack.
        
        This is the preferred method for adding undo records,
        as it accepts pre-constructed UndoRecord objects from RuntimeEngine.
        
        Args:
            record: UndoRecord to push
        """
        self.stack.append(record)
        
        # Limit stack size
        if len(self.stack) > self._max_stack_size:
            # Remove oldest record
            old_record = self.stack.pop(0)
            self._cleanup_backup(old_record)
        
        print(f"📝 Pushed undo record: {record.capability_id} (stack size: {len(self.stack)})", file=sys.stderr)
    
    def rollback(self, steps: int = 1, signal_bus=None) -> List[UndoRecord]:
        """
        Undo last N operations.
        
        Args:
            steps: Number of operations to undo
            signal_bus: Optional SignalBus for emitting governance signals
        
        Returns:
            List of descriptions of undone operations
        
        Raises:
            ValueError: If steps > available operations
        """
        if steps > len(self.stack):
            raise ValueError(
                f"Cannot undo {steps} operations, only {len(self.stack)} available"
            )
        
        undone = []
        
        for _ in range(steps):
            if not self.stack:
                break
            
            record = self.stack.pop()
            
            try:
                # Execute undo using the record's method
                record.execute_undo()
                undone.append(record)
                print(f"↩️  Undone: {record.description}")
                
                # Emit ROLLBACK_TRIGGERED signal (if signal_bus available)
                if signal_bus:
                    from governance.signals.models import SignalType, SignalSeverity, SignalSource
                    signal_bus.append(
                        capability_id=record.capability_id,
                        signal_type=SignalType.ROLLBACK_TRIGGERED,
                        severity=SignalSeverity.HIGH,
                        source=SignalSource.RUNTIME,
                        metadata={
                            "operation_id": record.operation_id,
                            "description": record.description
                        }
                    )
                
                # Cleanup backup
                self._cleanup_backup(record)
            
            except Exception as e:
                print(f"❌ Failed to undo {record.description}: {e}")
                # Re-add to stack if undo failed
                self.stack.append(record)
                raise
        
        return undone
    
    def peek(self, count: int = 5) -> List[Dict[str, Any]]:
        """
        View recent operations without undoing.
        
        Args:
            count: Number of recent operations to view
        
        Returns:
            List of operation dictionaries
        """
        recent = self.stack[-count:] if len(self.stack) >= count else self.stack
        return [record.to_dict() for record in reversed(recent)]
    
    def clear(self) -> None:
        """
        Clear all undo history and backups.
        
        This is irreversible!
        """
        # Cleanup all backups
        for record in self.stack:
            self._cleanup_backup(record)
        
        self.stack.clear()
        
        # Clear backup directory
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
            self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        print("🗑️  Undo history cleared")
    
    def save_to_file(self, filepath: Path) -> None:
        """
        Save undo history to file (without handlers).
        
        Args:
            filepath: Path to save history
        """
        history = [record.to_dict() for record in self.stack]
        
        with open(filepath, "w") as f:
            json.dump(history, f, indent=2)
        
        print(f"💾 Undo history saved to {filepath}")
    
    def get_stack_size(self) -> int:
        """
        Get number of operations in undo stack.
        
        Returns:
            Stack size
        """
        return len(self.stack)
    
    def is_empty(self) -> bool:
        """
        Check if undo stack is empty.
        
        Returns:
            True if empty
        """
        return len(self.stack) == 0
    
    def _cleanup_backup(self, record: UndoRecord) -> None:
        """
        Cleanup backup data for a record.
        
        Args:
            record: UndoRecord to cleanup
        """
        # With closure-based undo, cleanup is handled by the closure itself
        # This method is kept for backward compatibility
        pass
    
    def __len__(self) -> int:
        """Get stack size (supports len())"""
        return len(self.stack)
    
    def __repr__(self) -> str:
        """String representation"""
        return f"<UndoManager: {len(self.stack)} operations in stack>"


def create_file_backup_undo(
    original_path: Path,
    backup_dir: Path,
) -> tuple[Callable[[], None], Dict[str, Any]]:
    """
    Create undo handler and backup data for file operations.
    
    This is a helper function to create undo handlers for file write/delete operations.
    
    Args:
        original_path: Path to the file being modified
        backup_dir: Directory to store backup
    
    Returns:
        Tuple of (undo_handler, backup_data)
    
    Example:
        >>> undo_handler, backup_data = create_file_backup_undo(
        ...     Path("/workspace/file.txt"),
        ...     Path("/workspace/.backups")
        ... )
        >>> # Modify file
        >>> # Later, call undo_handler() to restore
    """
    # Create backup
    backup_path = backup_dir / f"{original_path.name}.backup"
    
    if original_path.exists():
        if original_path.is_dir():
            shutil.copytree(original_path, backup_path)
        else:
            shutil.copy2(original_path, backup_path)
        
        existed = True
    else:
        existed = False
    
    def undo_handler():
        """Restore from backup"""
        if existed:
            # Restore original file
            if backup_path.is_dir():
                if original_path.exists():
                    shutil.rmtree(original_path)
                shutil.copytree(backup_path, original_path)
            else:
                shutil.copy2(backup_path, original_path)
        else:
            # File didn't exist, remove it
            if original_path.exists():
                if original_path.is_dir():
                    shutil.rmtree(original_path)
                else:
                    original_path.unlink()
    
    backup_data = {
        "backup_path": str(backup_path),
        "original_path": str(original_path),
        "existed": existed,
    }
    
    return undo_handler, backup_data


def create_move_undo(
    source_path: Path,
    dest_path: Path,
) -> tuple[Callable[[], None], Dict[str, Any]]:
    """
    Create undo handler for move operations.
    
    Args:
        source_path: Original source path
        dest_path: Destination path
    
    Returns:
        Tuple of (undo_handler, backup_data)
    """
    def undo_handler():
        """Move back to original location"""
        if dest_path.exists():
            shutil.move(str(dest_path), str(source_path))
    
    backup_data = {
        "source_path": str(source_path),
        "dest_path": str(dest_path),
    }
    
    return undo_handler, backup_data
