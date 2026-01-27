"""
Capability Ingress API - 能力准入层

核心原则：
Capabilities are powers, not code.
All powers must pass through governance.

所有新能力（内部、第三方、AutoForge）必须通过提案流程。
Registry 只能通过治理批准写入。
"""

from .models import CapabilityProposal, ProposalSource, ProposalStatus
from .ingress_service import CapabilityIngressService
from .approval_service import CapabilityApprovalService

__all__ = [
    "CapabilityProposal",
    "ProposalSource",
    "ProposalStatus",
    "CapabilityIngressService",
    "CapabilityApprovalService",
]
