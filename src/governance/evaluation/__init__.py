"""
Domain B: Governance Evaluation API (裁决生成层)

将 Signal 转换为 GovernanceProposal。
只能"建议"，不能"执行"。
"""

from .proposal import GovernanceProposal, ProposalType, ProposalStatus
from .health_authority import HealthAuthority
from .rules import EvaluationRules

__all__ = [
    "GovernanceProposal",
    "ProposalType",
    "ProposalStatus",
    "HealthAuthority",
    "EvaluationRules",
]
