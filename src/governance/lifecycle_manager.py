"""
Lifecycle Manager - The Executor

LifecycleManager is the ONLY component allowed to change capability lifecycle state.

Hard Rules:
- Implement explicit state transition table
- Invalid transitions MUST raise errors
- DEPRECATED is terminal unless explicitly extended later
- Runtime MUST reject execution for FROZEN capabilities
"""

from enum import Enum
from typing import Dict, Optional, Set
from datetime import datetime
from dataclasses import dataclass
import json
from pathlib import Path

from .signal_bus import SignalBus, SignalType, SignalSeverity


class CapabilityState(str, Enum):
    """Capability lifecycle states"""
    PROPOSED = "PROPOSED"      # Newly created, not yet active
    ACTIVE = "ACTIVE"          # Normal operation
    DEGRADING = "DEGRADING"    # Health issues detected
    FROZEN = "FROZEN"          # Execution blocked by governance
    DEPRECATED = "DEPRECATED"  # End of life (terminal)


# Explicit state transition table
ALLOWED_TRANSITIONS: Dict[CapabilityState, Set[CapabilityState]] = {
    CapabilityState.PROPOSED: {
        CapabilityState.ACTIVE,
        CapabilityState.DEPRECATED
    },
    CapabilityState.ACTIVE: {
        CapabilityState.DEGRADING,
        CapabilityState.FROZEN,
        CapabilityState.DEPRECATED
    },
    CapabilityState.DEGRADING: {
        CapabilityState.ACTIVE,  # Can recover
        CapabilityState.FROZEN,
        CapabilityState.DEPRECATED
    },
    CapabilityState.FROZEN: {
        CapabilityState.ACTIVE,  # Can be unfrozen
        CapabilityState.DEPRECATED
    },
    CapabilityState.DEPRECATED: set()  # Terminal state
}


@dataclass
class CapabilityLifecycle:
    """Capability lifecycle record"""
    capability_id: str
    state: CapabilityState
    previous_state: Optional[CapabilityState]
    changed_at: datetime
    changed_by: str  # Admin identity
    reason: str
    metadata: Dict


class StateTransitionError(Exception):
    """Raised when an invalid state transition is attempted"""
    pass


class LifecycleManager:
    """
    Lifecycle Manager - The ONLY component that can change capability state.
    
    This enforces governance decisions and maintains capability lifecycle.
    """
    
    def __init__(self, signal_bus: SignalBus, db_path: Optional[Path] = None):
        """
        Initialize Lifecycle Manager.
        
        Args:
            signal_bus: SignalBus instance for emitting lifecycle signals
            db_path: Path to lifecycle database (default: .ai-first/lifecycle.db)
        """
        self.signal_bus = signal_bus
        
        if db_path is None:
            db_path = Path.home() / ".ai-first" / "lifecycle.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._lifecycles: Dict[str, CapabilityLifecycle] = {}
        self._init_database()
        self._load_lifecycles()
    
    def _init_database(self):
        """Initialize lifecycle database"""
        import sqlite3
        
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS capability_lifecycles (
                    capability_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    previous_state TEXT,
                    changed_at TEXT NOT NULL,
                    changed_by TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_state 
                ON capability_lifecycles(state)
            """)
            
            conn.commit()
    
    def _load_lifecycles(self):
        """Load all lifecycles from database"""
        import sqlite3
        
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM capability_lifecycles")
            
            for row in cursor:
                lifecycle = CapabilityLifecycle(
                    capability_id=row["capability_id"],
                    state=CapabilityState(row["state"]),
                    previous_state=CapabilityState(row["previous_state"]) if row["previous_state"] else None,
                    changed_at=datetime.fromisoformat(row["changed_at"]),
                    changed_by=row["changed_by"],
                    reason=row["reason"],
                    metadata=json.loads(row["metadata"] or "{}")
                )
                self._lifecycles[lifecycle.capability_id] = lifecycle
    
    def get_state(self, capability_id: str) -> CapabilityState:
        """
        Get current state of a capability.
        
        Returns ACTIVE by default if capability has no lifecycle record.
        """
        if capability_id in self._lifecycles:
            return self._lifecycles[capability_id].state
        return CapabilityState.ACTIVE  # Default state
    
    def transition(
        self,
        capability_id: str,
        new_state: CapabilityState,
        changed_by: str,
        reason: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Transition capability to a new state.
        
        This is the ONLY way to change capability state.
        Invalid transitions raise StateTransitionError.
        
        Args:
            capability_id: Capability to transition
            new_state: Target state
            changed_by: Admin identity
            reason: Human-readable reason for transition
            metadata: Optional metadata
        
        Raises:
            StateTransitionError: If transition is invalid
        """
        current_state = self.get_state(capability_id)
        
        # Check if transition is allowed
        if new_state not in ALLOWED_TRANSITIONS.get(current_state, set()):
            raise StateTransitionError(
                f"Invalid transition from {current_state.value} to {new_state.value} "
                f"for capability {capability_id}. "
                f"Allowed transitions: {[s.value for s in ALLOWED_TRANSITIONS.get(current_state, set())]}"
            )
        
        # Check terminal state
        if current_state == CapabilityState.DEPRECATED:
            raise StateTransitionError(
                f"Cannot transition from DEPRECATED state for capability {capability_id}"
            )
        
        # Create lifecycle record
        lifecycle = CapabilityLifecycle(
            capability_id=capability_id,
            state=new_state,
            previous_state=current_state,
            changed_at=datetime.now(),
            changed_by=changed_by,
            reason=reason,
            metadata=metadata or {}
        )
        
        # Save to database
        import sqlite3
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO capability_lifecycles
                (capability_id, state, previous_state, changed_at, changed_by, reason, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                capability_id,
                new_state.value,
                current_state.value if current_state != CapabilityState.ACTIVE or capability_id in self._lifecycles else None,
                lifecycle.changed_at.isoformat(),
                changed_by,
                reason,
                json.dumps(metadata or {})
            ))
            conn.commit()
        
        # Update in-memory cache
        self._lifecycles[capability_id] = lifecycle
        
        # Emit governance signal
        signal_metadata = {
            "previous_state": current_state.value,
            "new_state": new_state.value,
            "changed_by": changed_by,
            "reason": reason
        }
        if metadata:
            signal_metadata.update(metadata)
        
        self.signal_bus.emit(
            capability_id=capability_id,
            signal_type=SignalType.LIFECYCLE_CHANGED,
            severity=SignalSeverity.HIGH,
            metadata=signal_metadata
        )
    
    def freeze(
        self,
        capability_id: str,
        changed_by: str,
        reason: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Freeze a capability (block execution).
        
        This is a convenience method for the common FROZEN transition.
        
        Args:
            capability_id: Capability to freeze
            changed_by: Admin identity
            reason: Reason for freezing
            metadata: Optional metadata
        """
        self.transition(
            capability_id=capability_id,
            new_state=CapabilityState.FROZEN,
            changed_by=changed_by,
            reason=reason,
            metadata=metadata
        )
    
    def unfreeze(
        self,
        capability_id: str,
        changed_by: str,
        reason: str
    ) -> None:
        """
        Unfreeze a capability (restore to ACTIVE).
        
        Args:
            capability_id: Capability to unfreeze
            changed_by: Admin identity
            reason: Reason for unfreezing
        """
        current_state = self.get_state(capability_id)
        if current_state != CapabilityState.FROZEN:
            raise StateTransitionError(
                f"Cannot unfreeze capability {capability_id} in state {current_state.value}"
            )
        
        self.transition(
            capability_id=capability_id,
            new_state=CapabilityState.ACTIVE,
            changed_by=changed_by,
            reason=reason
        )
    
    def is_executable(self, capability_id: str) -> bool:
        """
        Check if a capability is executable.
        
        FROZEN and DEPRECATED capabilities are not executable.
        
        Args:
            capability_id: Capability to check
        
        Returns:
            True if executable, False otherwise
        """
        state = self.get_state(capability_id)
        return state not in {CapabilityState.FROZEN, CapabilityState.DEPRECATED}
    
    def get_all_lifecycles(self) -> Dict[str, CapabilityLifecycle]:
        """Get all capability lifecycles"""
        return self._lifecycles.copy()
