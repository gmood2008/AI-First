"""
Core type definitions for AI-First Runtime.

This module defines the fundamental data structures used throughout the runtime.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel


class ExecutionStatus(str, Enum):
    """Status of a capability execution"""
    SUCCESS = "success"
    FAILED = "failed"
    DENIED = "denied"  # User denied confirmation
    ERROR = "error"


@dataclass
class ExecutionContext:
    """
    Execution environment and state for a capability invocation.
    
    This provides the runtime with necessary context about the execution environment,
    including workspace isolation, user identity, and callback mechanisms.
    """
    
    user_id: str
    """Unique identifier for the user executing the capability"""
    
    workspace_root: Path
    """Root directory for filesystem operations (sandbox boundary)"""
    
    session_id: str
    """Unique identifier for this execution session"""
    
    confirmation_callback: Optional[Callable[[str, Dict[str, Any]], bool]] = None
    """Callback function for user confirmation requests"""
    
    undo_enabled: bool = True
    """Whether undo recording is enabled for this execution"""
    
    backup_dir: Optional[Path] = None
    """Directory for storing operation backups"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional context metadata"""
    
    def __post_init__(self):
        """Initialize derived fields"""
        if self.backup_dir is None:
            self.backup_dir = self.workspace_root / ".ai-first" / "backups" / self.session_id
            self.backup_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class ActionOutput:
    """
    Output from a Handler's execute method.
    
    This is the bridge between Handler execution and RuntimeEngine's undo management.
    Handlers return this instead of a plain dict, allowing them to provide undo closures.
    """
    
    result: Dict[str, Any]
    """The actual output data (what the LLM sees)"""
    
    undo_closure: Optional[Callable[[], None]] = None
    """
    A closure that captures all data needed for undo.
    When called, it should reverse the operation.
    
    Example:
        def undo():
            shutil.copy(backup_path, original_path)
        return ActionOutput(result={...}, undo_closure=undo)
    """
    
    description: str = ""
    """Human-readable description of what was done (for undo history)"""


@dataclass
class ExecutionResult:
    """
    Result of a capability execution.
    
    This encapsulates both successful and failed executions, providing
    detailed information about what happened.
    """
    
    capability_id: str
    """ID of the executed capability"""
    
    status: ExecutionStatus
    """Execution status"""
    
    outputs: Dict[str, Any]
    """Output values as defined in capability spec"""
    
    error_message: Optional[str] = None
    """Error message if execution failed"""
    
    execution_time_ms: float = 0.0
    """Execution duration in milliseconds"""
    
    undo_available: bool = False
    """Whether this operation can be undone"""
    
    undo_record: Optional['UndoRecord'] = None
    """Undo record if operation supports undo"""
    
    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional execution metadata"""
    
    def is_success(self) -> bool:
        """Check if execution was successful"""
        return self.status == ExecutionStatus.SUCCESS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "capability_id": self.capability_id,
            "status": self.status.value,
            "outputs": self.outputs,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "undo_available": self.undo_available,
            "metadata": self.metadata,
        }


@dataclass
class UndoRecord:
    """
    Record of a reversible operation.
    
    This stores all information needed to undo an operation,
    including the undo closure function.
    """
    
    operation_id: str
    """Unique ID for this operation"""
    
    capability_id: str
    """ID of the capability that was executed"""
    
    timestamp: datetime
    """When the operation was executed"""
    
    params: Dict[str, Any]
    """Parameters used for the operation"""
    
    undo_function: Callable[[], None]
    """Function to execute for undo (closure with captured state)"""
    
    undo_args: Dict[str, Any] = field(default_factory=dict)
    """Arguments for undo function (for serialization/logging)"""
    
    description: str = ""
    """Human-readable description of what was done"""
    
    def execute_undo(self) -> None:
        """Execute the undo operation"""
        self.undo_function()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization (excluding function)"""
        return {
            "operation_id": self.operation_id,
            "capability_id": self.capability_id,
            "timestamp": self.timestamp.isoformat(),
            "params": self.params,
            "undo_args": self.undo_args,
            "description": self.description,
        }


class SecurityError(Exception):
    """Raised when a security constraint is violated"""
    pass


class ValidationError(Exception):
    """Raised when parameter validation fails"""
    pass


class CapabilityNotFoundError(Exception):
    """Raised when a requested capability doesn't exist"""
    pass


class ConfirmationDeniedError(Exception):
    """Raised when user denies confirmation for a dangerous operation"""
    pass


@dataclass
class CapabilityInfo:
    """
    Information about a registered capability.
    
    Used for listing and inspecting available capabilities.
    """
    capability_id: str
    description: str
    side_effects: List[str]
    requires_confirmation: bool
    is_atomic: bool
    cost_model: str
