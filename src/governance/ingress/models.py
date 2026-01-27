"""
Capability Proposal Models - 能力提案模型

所有新能力必须作为 Proposal 进入系统。
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional
import json
import uuid

from specs.v3.capability_schema import CapabilitySpec


class ProposalSource(str, Enum):
    """提案来源"""
    INTERNAL = "internal"
    THIRD_PARTY = "third_party"
    AUTOFORGE = "autoforge"


class ProposalStatus(str, Enum):
    """提案状态"""
    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class CapabilityProposal:
    """
    能力提案 - 所有新能力必须通过提案流程
    
    状态机规则：
    PENDING_REVIEW -> APPROVED -> Registry.ACTIVE
    PENDING_REVIEW -> REJECTED -> Archive
    """
    proposal_id: str
    capability_spec: CapabilitySpec
    risk_summary: str
    source: ProposalSource
    submitted_by: str
    justification: str
    status: ProposalStatus
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    approval_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于存储"""
        return {
            "proposal_id": self.proposal_id,
            "capability_spec": json.dumps(self.capability_spec.model_dump(mode='json')),
            "risk_summary": self.risk_summary,
            "source": self.source.value,
            "submitted_by": self.submitted_by,
            "justification": self.justification,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewer_id": self.reviewer_id,
            "rejection_reason": self.rejection_reason,
            "approval_id": self.approval_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityProposal":
        """从数据库记录创建"""
        from specs.v3.capability_schema import CapabilitySpec
        
        return cls(
            proposal_id=data["proposal_id"],
            capability_spec=CapabilitySpec.model_validate(json.loads(data["capability_spec"])),
            risk_summary=data["risk_summary"],
            source=ProposalSource(data["source"]),
            submitted_by=data["submitted_by"],
            justification=data["justification"],
            status=ProposalStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            reviewed_at=datetime.fromisoformat(data["reviewed_at"]) if data.get("reviewed_at") else None,
            reviewer_id=data.get("reviewer_id"),
            rejection_reason=data.get("rejection_reason"),
            approval_id=data.get("approval_id")
        )
    
    def can_transition_to(self, new_status: ProposalStatus) -> bool:
        """检查是否可以转换到新状态"""
        if self.status == ProposalStatus.PENDING_REVIEW:
            return new_status in {ProposalStatus.APPROVED, ProposalStatus.REJECTED}
        return False  # APPROVED 和 REJECTED 是终端状态
