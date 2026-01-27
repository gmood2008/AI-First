"""
Capability Ingress API - 能力准入 API 门面

这是给系统 / Agent / UI 调用的 API。
所有新能力必须通过此 API 进入系统。
"""

from typing import List, Optional
from datetime import datetime

from .ingress_service import CapabilityIngressService
from .approval_service import CapabilityApprovalService
from .models import CapabilityProposal, ProposalSource, ProposalStatus
from specs.v3.capability_schema import CapabilitySpec
from runtime.registry import CapabilityRegistry
from governance.lifecycle.lifecycle_service import LifecycleService
from governance.audit.audit_log import AuditLog


class CapabilityIngressAPI:
    """
    Capability Ingress API - 能力准入 API 门面
    
    这是所有新能力进入系统的唯一入口。
    
    核心原则：
    Capabilities are powers, not code.
    All powers must pass through governance.
    """
    
    def __init__(
        self,
        ingress_service: Optional[CapabilityIngressService] = None,
        approval_service: Optional[CapabilityApprovalService] = None,
        registry: Optional[CapabilityRegistry] = None,
        lifecycle_service: Optional[LifecycleService] = None,
        audit_log: Optional[AuditLog] = None
    ):
        """
        初始化 Ingress API
        
        Args:
            ingress_service: Ingress Service 实例
            approval_service: Approval Service 实例
            registry: Capability Registry
            lifecycle_service: Lifecycle Service
            audit_log: Audit Log
        """
        self.ingress_service = ingress_service or CapabilityIngressService()
        self.registry = registry or CapabilityRegistry(governance_enforced=True)
        self.lifecycle_service = lifecycle_service
        self.audit_log = audit_log or AuditLog()
        
        if approval_service is None:
            self.approval_service = CapabilityApprovalService(
                ingress_service=self.ingress_service,
                registry=self.registry,
                lifecycle_service=self.lifecycle_service,
                audit_log=self.audit_log
            )
        else:
            self.approval_service = approval_service
    
    def submit_proposal(
        self,
        capability_spec: CapabilitySpec,
        source: ProposalSource,
        submitted_by: str,
        justification: str
    ) -> CapabilityProposal:
        """
        POST /governance/capabilities/proposals
        
        提交能力提案
        
        Args:
            capability_spec: 能力规范
            source: 提案来源
            submitted_by: 提交者
            justification: 理由（必需）
        
        Returns:
            CapabilityProposal 对象
        """
        return self.ingress_service.submit_proposal(
            capability_spec=capability_spec,
            source=source,
            submitted_by=submitted_by,
            justification=justification
        )
    
    def submit_batch_proposals(
        self,
        capability_specs: List[CapabilitySpec],
        source: ProposalSource,
        submitted_by: str,
        justification: str
    ) -> List[CapabilityProposal]:
        """
        POST /governance/capabilities/proposals/batch
        
        批量提交提案
        
        规则：
        - 每个能力成为独立的 Proposal
        - 不允许批量批准
        - 不允许批量激活
        - 允许部分批准
        
        Args:
            capability_specs: 能力规范列表
            source: 提案来源
            submitted_by: 提交者
            justification: 理由
        
        Returns:
            Proposal 列表
        """
        return self.ingress_service.submit_batch_proposals(
            capability_specs=capability_specs,
            source=source,
            submitted_by=submitted_by,
            justification=justification
        )
    
    def approve_proposal(
        self,
        proposal_id: str,
        reviewer_id: str,
        reason: str = ""
    ) -> None:
        """
        POST /governance/capabilities/proposals/{id}/approve
        
        批准提案
        
        Args:
            proposal_id: 提案 ID
            reviewer_id: 审核者 ID
            reason: 批准原因
        """
        self.approval_service.approve_proposal(
            proposal_id=proposal_id,
            reviewer_id=reviewer_id,
            reason=reason
        )
    
    def reject_proposal(
        self,
        proposal_id: str,
        reviewer_id: str,
        rejection_reason: str
    ) -> None:
        """
        POST /governance/capabilities/proposals/{id}/reject
        
        拒绝提案
        
        Args:
            proposal_id: 提案 ID
            reviewer_id: 审核者 ID
            rejection_reason: 拒绝原因（必需）
        """
        self.approval_service.reject_proposal(
            proposal_id=proposal_id,
            reviewer_id=reviewer_id,
            rejection_reason=rejection_reason
        )
    
    def get_proposal(self, proposal_id: str) -> Optional[CapabilityProposal]:
        """获取提案"""
        return self.ingress_service.get_proposal(proposal_id)
    
    def get_pending_proposals(self) -> List[CapabilityProposal]:
        """获取所有待审核的提案"""
        return self.ingress_service.get_pending_proposals()
