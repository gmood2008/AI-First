"""
Security sandbox for path validation and workspace isolation.

This module ensures all filesystem operations stay within the workspace boundary.
"""

from pathlib import Path
from typing import Optional

from ..types import SecurityError


class PathSandbox:
    """
    Enforces workspace isolation for filesystem operations.
    
    This class ensures that all file paths are resolved within the workspace
    directory and prevents path traversal attacks.
    """
    
    def __init__(self, workspace_root: Path):
        """
        Initialize sandbox with workspace root.
        
        Args:
            workspace_root: Root directory for all operations
        """
        self.workspace_root = workspace_root.resolve()
        
        # Ensure workspace exists
        self.workspace_root.mkdir(parents=True, exist_ok=True)
    
    def validate_path(self, path: str) -> Path:
        """
        Validate and resolve a path within the workspace.
        
        This method:
        1. Resolves the path to an absolute path
        2. Checks if it's within the workspace boundary
        3. Returns the validated path
        
        Args:
            path: Relative or absolute path string
        
        Returns:
            Resolved Path object within workspace
        
        Raises:
            SecurityError: If path escapes workspace
        
        Examples:
            >>> sandbox = PathSandbox(Path("/workspace"))
            >>> sandbox.validate_path("file.txt")
            Path("/workspace/file.txt")
            
            >>> sandbox.validate_path("../../../etc/passwd")
            SecurityError: Path escapes workspace
        """
        # Handle absolute paths
        if Path(path).is_absolute():
            full_path = Path(path).resolve()
        else:
            full_path = (self.workspace_root / path).resolve()
        
        # Security check: ensure path is within workspace
        try:
            full_path.relative_to(self.workspace_root)
        except ValueError:
            raise SecurityError(
                f"Path '{path}' escapes workspace boundary. "
                f"Workspace: {self.workspace_root}, "
                f"Resolved: {full_path}"
            )
        
        return full_path
    
    def is_within_workspace(self, path: Path) -> bool:
        """
        Check if a path is within the workspace.
        
        Args:
            path: Path to check
        
        Returns:
            True if within workspace
        """
        try:
            path.resolve().relative_to(self.workspace_root)
            return True
        except ValueError:
            return False
    
    def get_relative_path(self, path: Path) -> Path:
        """
        Get relative path from workspace root.
        
        Args:
            path: Absolute path
        
        Returns:
            Relative path from workspace root
        
        Raises:
            SecurityError: If path is outside workspace
        """
        try:
            return path.resolve().relative_to(self.workspace_root)
        except ValueError:
            raise SecurityError(f"Path '{path}' is outside workspace")
    
    def __repr__(self) -> str:
        """String representation"""
        return f"<PathSandbox: {self.workspace_root}>"


class PermissionChecker:
    """
    Validates that operations match declared side effects.
    
    This ensures that handlers don't perform operations they haven't
    declared in their capability specification.
    """
    
    def __init__(self):
        """Initialize permission checker"""
        pass
    
    def check_operation(
        self, 
        declared_side_effects: list, 
        operation_type: str
    ) -> None:
        """
        Check if an operation is allowed based on declared side effects.
        
        Args:
            declared_side_effects: List of side effects from capability spec
            operation_type: Type of operation being performed
        
        Raises:
            SecurityError: If operation not declared
        
        Examples:
            >>> checker = PermissionChecker()
            >>> checker.check_operation(["filesystem_write"], "write_file")
            # OK
            
            >>> checker.check_operation(["read_only"], "write_file")
            SecurityError: Operation 'write_file' not allowed
        """
        # Map operation types to required side effects
        operation_map = {
            "read_file": ["read_only", "filesystem_read"],
            "write_file": ["filesystem_write"],
            "delete_file": ["filesystem_write"],
            "network_request": ["network_read", "network_write"],
            "system_exec": ["system_exec"],
        }
        
        required_effects = operation_map.get(operation_type, [])
        
        # Check if any required effect is declared
        if required_effects:
            if not any(effect in declared_side_effects for effect in required_effects):
                raise SecurityError(
                    f"Operation '{operation_type}' requires one of {required_effects}, "
                    f"but only {declared_side_effects} are declared"
                )
    
    def is_read_only(self, side_effects: list) -> bool:
        """
        Check if capability is read-only.
        
        Args:
            side_effects: List of side effects
        
        Returns:
            True if read-only
        """
        return side_effects == ["read_only"] or len(side_effects) == 0
    
    def is_dangerous(self, side_effects: list) -> bool:
        """
        Check if capability has dangerous side effects.
        
        Args:
            side_effects: List of side effects
        
        Returns:
            True if dangerous
        """
        dangerous_effects = {
            "filesystem_write",
            "network_write",
            "system_exec",
        }
        return any(effect in dangerous_effects for effect in side_effects)


class ConfirmationGate:
    """
    Intercepts dangerous operations and requests user approval.
    
    This implements the confirmation flow for operations that require
    explicit user consent.
    """
    
    def __init__(self):
        """Initialize confirmation gate"""
        self._auto_approve = False
    
    def check(
        self,
        capability_id: str,
        description: str,
        side_effects: list,
        params: dict,
        undo_strategy: str,
        callback: Optional[callable] = None,
    ) -> bool:
        """
        Check if operation should proceed.
        
        Args:
            capability_id: ID of capability
            description: Human-readable description
            side_effects: List of side effects
            params: Execution parameters
            undo_strategy: Undo strategy description
            callback: Confirmation callback function
        
        Returns:
            True if approved, False if denied
        """
        # If auto-approve is enabled, always approve
        if self._auto_approve:
            return True
        
        # If no callback, deny by default
        if callback is None:
            return False
        
        # Format confirmation message
        message = self._format_message(
            capability_id,
            description,
            side_effects,
            params,
            undo_strategy,
        )
        
        # Call confirmation callback
        try:
            return callback(message, params)
        except Exception as e:
            print(f"⚠️  Confirmation callback failed: {e}")
            return False
    
    def _format_message(
        self,
        capability_id: str,
        description: str,
        side_effects: list,
        params: dict,
        undo_strategy: str,
    ) -> str:
        """Format confirmation message"""
        lines = [
            "=" * 70,
            "⚠️  CONFIRMATION REQUIRED",
            "=" * 70,
            "",
            f"Capability: {capability_id}",
            f"Description: {description}",
            f"Side Effects: {', '.join(side_effects)}",
            "",
            "Parameters:",
        ]
        
        for key, value in params.items():
            # Truncate long values
            value_str = str(value)
            if len(value_str) > 100:
                value_str = value_str[:100] + "..."
            lines.append(f"  {key}: {value_str}")
        
        lines.extend([
            "",
            f"Undo Strategy: {undo_strategy}",
            "",
            "=" * 70,
        ])
        
        return "\n".join(lines)
    
    def enable_auto_approve(self) -> None:
        """Enable auto-approval (for testing)"""
        self._auto_approve = True
        print("⚠️  Auto-approval enabled (unsafe for production)")
    
    def disable_auto_approve(self) -> None:
        """Disable auto-approval"""
        self._auto_approve = False
