"""AI-First Runtime - Core modules"""

from .types import ExecutionContext, ExecutionResult, ExecutionStatus
from .handler import ActionHandler
from .registry import CapabilityRegistry
from .engine import RuntimeEngine
from .undo.manager import UndoManager

__version__ = "0.1.0"

__all__ = [
    "ExecutionContext",
    "ExecutionResult",
    "ExecutionStatus",
    "ActionHandler",
    "CapabilityRegistry",
    "RuntimeEngine",
    "UndoManager",
]
