"""
Governance Proposal Model - 治理提案

Proposal 只是建议，不能直接执行。
只有 Lifecycle Service 可以执行提案。
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any
import json


class ProposalType(str, Enum):
    """提案类型"""
    FIX = "FIX"
    SPLIT = "SPLIT"
    UPGRADE_RISK = "UPGRADE_RISK"
    FREEZE = "FREEZE"
    DEPRECATE = "DEPRECATE"
    # Pack-related proposal types
    PACK_CREATE = "PACK_CREATE"
    PACK_FREEZE = "PACK_FREEZE"


class ProposalStatus(str, Enum):
    """提案状态"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTED = "EXECUTED"


@dataclass
class GovernanceProposal:
    """
    治理提案 - 只是建议，不直接执行
    
    必须包含：
    - evidence（signal ids）
    - confidence（0~1）
    - reason（可审计文本）
    """
    proposal_id: str
    capability_id: str
    proposal_type: ProposalType
    evidence_signal_ids: List[str]  # 证据 Signal IDs
    confidence: float  # 0~1 置信度
    reason: str  # 可审计文本
    created_at: datetime
    status: ProposalStatus
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于存储"""
        return {
            "proposal_id": self.proposal_id,
            "capability_id": self.capability_id,
            "proposal_type": self.proposal_type.value,
            "evidence_signal_ids": json.dumps(self.evidence_signal_ids),
            "confidence": self.confidence,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "metadata": json.dumps(self.metadata)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GovernanceProposal":
        """从数据库记录创建"""
        return cls(
            proposal_id=data["proposal_id"],
            capability_id=data["capability_id"],
            proposal_type=ProposalType(data["proposal_type"]),
            evidence_signal_ids=json.loads(data["evidence_signal_ids"]),
            confidence=float(data["confidence"]),
            reason=data["reason"],
            created_at=datetime.fromisoformat(data["created_at"]),
            status=ProposalStatus(data["status"]),
            metadata=json.loads(data["metadata"] or "{}")
        )
