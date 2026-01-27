"""
Signal Bus - The Sensors

The Signal Bus is the governance event source, not a debug log.
It passively records all friction and failure signals emitted by the system.

Hard Constraints:
- Signals are append-only (immutable)
- No component except SignalBus may write to governance signals
- Signals MUST be replayable in the future
- No aggregation on write
"""

import sqlite3
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import json
from dataclasses import dataclass, asdict


class SignalType(str, Enum):
    """Governance signal types"""
    CAPABILITY_NOT_FOUND = "CAPABILITY_NOT_FOUND"
    POLICY_DENIED = "POLICY_DENIED"
    ROLLBACK_TRIGGERED = "ROLLBACK_TRIGGERED"
    HUMAN_REJECTED = "HUMAN_REJECTED"
    GOVERNANCE_REJECTED = "GOVERNANCE_REJECTED"
    LIFECYCLE_CHANGED = "LIFECYCLE_CHANGED"
    HEALTH_DEGRADED = "HEALTH_DEGRADED"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    EXECUTION_SUCCESS = "EXECUTION_SUCCESS"


class SignalSeverity(str, Enum):
    """Signal severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class GovernanceSignal:
    """Immutable governance signal record"""
    signal_id: str
    capability_id: str
    workflow_id: Optional[str]
    signal_type: SignalType
    severity: SignalSeverity
    timestamp: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "signal_id": self.signal_id,
            "capability_id": self.capability_id,
            "workflow_id": self.workflow_id,
            "signal_type": self.signal_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": json.dumps(self.metadata)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GovernanceSignal":
        """Create from database record"""
        return cls(
            signal_id=data["signal_id"],
            capability_id=data["capability_id"],
            workflow_id=data.get("workflow_id"),
            signal_type=SignalType(data["signal_type"]),
            severity=SignalSeverity(data["severity"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=json.loads(data["metadata"] or "{}")
        )


class SignalBus:
    """
    The Signal Bus - Immutable append-only event log for governance signals.
    
    This is the ONLY component that can write to governance signals.
    All signals are immutable and replayable.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize Signal Bus.
        
        Args:
            db_path: Path to SQLite database (default: .ai-first/governance.db)
        """
        if db_path is None:
            db_path = Path.home() / ".ai-first" / "governance.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize the governance_signals table"""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS governance_signals (
                    signal_id TEXT PRIMARY KEY,
                    capability_id TEXT NOT NULL,
                    workflow_id TEXT,
                    signal_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
            """)
            
            # Create indexes for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_capability_id 
                ON governance_signals(capability_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_signal_type 
                ON governance_signals(signal_type)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON governance_signals(timestamp)
            """)
            
            conn.commit()
    
    def emit(
        self,
        capability_id: str,
        signal_type: SignalType,
        severity: SignalSeverity,
        workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Emit a governance signal (append-only write).
        
        This is the ONLY way to write signals. All signals are immutable.
        
        Args:
            capability_id: Capability that triggered the signal
            signal_type: Type of signal
            severity: Severity level
            workflow_id: Optional workflow identifier
            metadata: Optional additional metadata
        
        Returns:
            signal_id: Unique identifier for the emitted signal
        """
        signal_id = f"sig_{datetime.now().timestamp()}_{id(self)}"
        timestamp = datetime.now()
        metadata = metadata or {}
        
        signal = GovernanceSignal(
            signal_id=signal_id,
            capability_id=capability_id,
            workflow_id=workflow_id,
            signal_type=signal_type,
            severity=severity,
            timestamp=timestamp,
            metadata=metadata
        )
        
        # Append-only write (immutable)
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO governance_signals 
                (signal_id, capability_id, workflow_id, signal_type, severity, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                signal.signal_id,
                signal.capability_id,
                signal.workflow_id,
                signal.signal_type.value,
                signal.severity.value,
                signal.timestamp.isoformat(),
                json.dumps(signal.metadata)
            ))
            conn.commit()
        
        return signal_id
    
    def get_signals(
        self,
        capability_id: Optional[str] = None,
        signal_type: Optional[SignalType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[GovernanceSignal]:
        """
        Read signals (replayable, no aggregation).
        
        Args:
            capability_id: Filter by capability ID
            signal_type: Filter by signal type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum number of signals to return
        
        Returns:
            List of governance signals
        """
        query = "SELECT * FROM governance_signals WHERE 1=1"
        params = []
        
        if capability_id:
            query += " AND capability_id = ?"
            params.append(capability_id)
        
        if signal_type:
            query += " AND signal_type = ?"
            params.append(signal_type.value)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        signals = []
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            
            for row in cursor:
                signals.append(GovernanceSignal.from_dict(dict(row)))
        
        return signals
    
    def replay(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[GovernanceSignal]:
        """
        Replay all signals in chronological order.
        
        This is used for governance analysis and auditing.
        
        Args:
            start_time: Start of replay window
            end_time: End of replay window
        
        Returns:
            List of signals in chronological order
        """
        return self.get_signals(
            start_time=start_time,
            end_time=end_time,
            limit=None
        )
    
    def get_signal_count(
        self,
        capability_id: str,
        signal_type: Optional[SignalType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> int:
        """
        Get count of signals (for metrics, but no aggregation on write).
        
        This is a read-only aggregation operation.
        """
        query = "SELECT COUNT(*) FROM governance_signals WHERE capability_id = ?"
        params = [capability_id]
        
        if signal_type:
            query += " AND signal_type = ?"
            params.append(signal_type.value)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
        
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()[0]
