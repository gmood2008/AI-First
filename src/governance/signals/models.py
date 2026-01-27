"""
Signal Models - 事实层数据模型

Signal 只记录事实，不包含判断逻辑。
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional


class SignalType(str, Enum):
    """Signal 类型 - 只记录事实"""
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
    """Signal 严重程度"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SignalSource(str, Enum):
    """Signal 来源"""
    RUNTIME = "RUNTIME"
    POLICY = "POLICY"
    HUMAN_GATE = "HUMAN_GATE"
    GOVERNANCE = "GOVERNANCE"
    WORKFLOW = "WORKFLOW"


@dataclass
class Signal:
    """
    Signal 数据模型 - 只记录事实
    
    禁止事项：
    - ❌ update / delete
    - ❌ 在这里计算健康度
    - ❌ 自动触发生命周期变更
    """
    signal_id: str
    capability_id: str
    workflow_id: Optional[str]
    signal_type: SignalType
    severity: SignalSeverity
    source: SignalSource
    timestamp: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于存储"""
        import json
        return {
            "signal_id": self.signal_id,
            "capability_id": self.capability_id,
            "workflow_id": self.workflow_id,
            "signal_type": self.signal_type.value,
            "severity": self.severity.value,
            "source": self.source.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": json.dumps(self.metadata)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Signal":
        """从数据库记录创建"""
        import json
        return cls(
            signal_id=data["signal_id"],
            capability_id=data["capability_id"],
            workflow_id=data.get("workflow_id"),
            signal_type=SignalType(data["signal_type"]),
            severity=SignalSeverity(data["severity"]),
            source=SignalSource(data["source"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=json.loads(data["metadata"] or "{}")
        )
