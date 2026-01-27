"""
Governance Proposal Model V2 - 治理提案模型 V2

定义 schema: GovernanceProposal
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import uuid


class ProposalTypeV2(str, Enum):
    """提案类型"""
    FIX = "FIX"
    SPLIT = "SPLIT"
    FREEZE = "FREEZE"
    PROMOTE = "PROMOTE"
    DEPRECATE = "DEPRECATE"
    # Pack-related proposal types
    PACK_CREATE = "PACK_CREATE"
    PACK_FREEZE = "PACK_FREEZE"


class ProposalStatusV2(str, Enum):
    """提案状态"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class GovernanceProposalV2:
    """
    治理提案 V2
    
    必需字段：
    - proposal_id
    - proposal_type (FIX / SPLIT / FREEZE / PROMOTE / DEPRECATE)
    - target_capability_id
    - triggering_evidence (signals, metrics, references)
    - created_at
    - created_by (system / admin / autoforge)
    - status (PENDING / APPROVED / REJECTED / EXPIRED)
    """
    proposal_id: str
    proposal_type: ProposalTypeV2
    target_capability_id: str
    triggering_evidence: Dict[str, Any]  # signals, metrics, references
    created_at: datetime
    created_by: str  # system / admin / autoforge
    status: ProposalStatusV2
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于存储"""
        return {
            "proposal_id": self.proposal_id,
            "proposal_type": self.proposal_type.value,
            "target_capability_id": self.target_capability_id,
            "triggering_evidence": json.dumps(self.triggering_evidence),
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status.value,
            "metadata": json.dumps(self.metadata)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GovernanceProposalV2":
        """从数据库记录创建"""
        return cls(
            proposal_id=data["proposal_id"],
            proposal_type=ProposalTypeV2(data["proposal_type"]),
            target_capability_id=data["target_capability_id"],
            triggering_evidence=json.loads(data["triggering_evidence"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            created_by=data["created_by"],
            status=ProposalStatusV2(data["status"]),
            metadata=json.loads(data["metadata"] or "{}")
        )
