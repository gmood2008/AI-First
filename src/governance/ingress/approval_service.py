"""
Capability Approval Service - 能力审批服务

人工审批接口。
只有通过审批的能力才能进入 Registry。
"""

import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime
import json
import uuid

from .models import CapabilityProposal, ProposalStatus
from .ingress_service import CapabilityIngressService
from runtime.registry import CapabilityRegistry
from runtime.handler import ActionHandler
from governance.lifecycle.lifecycle_service import LifecycleService
from governance.lifecycle.state_machine import CapabilityState
from governance.audit.audit_log import AuditLog, AuditEvent, AuditEventType


class CapabilityApprovalService:
    """
    Capability Approval Service - 能力审批服务
    
    职责：
    - 批准提案 → 激活能力
    - 拒绝提案 → 归档
    
    禁止事项：
    - ❌ 不能绕过提案流程
    - ❌ 不能批量激活
    """
    
    def __init__(
        self,
        ingress_service: CapabilityIngressService,
        registry: CapabilityRegistry,
        lifecycle_service: Optional[LifecycleService] = None,
        audit_log: Optional[AuditLog] = None
    ):
        """
        初始化 Approval Service
        
        Args:
            ingress_service: Ingress Service 实例
            registry: Capability Registry（只读，只能通过此服务写入）
            lifecycle_service: Lifecycle Service（可选）
            audit_log: Audit Log（可选）
        """
        self.ingress_service = ingress_service
        self.registry = registry
        self.lifecycle_service = lifecycle_service
        self.audit_log = audit_log
    
    def approve_proposal(
        self,
        proposal_id: str,
        reviewer_id: str,
        reason: str = ""
    ) -> None:
        """
        POST /governance/capabilities/proposals/{id}/approve
        
        批准提案
        
        行为：
        - 注册能力到 CapabilityRegistry
        - 设置 lifecycle_state = ACTIVE
        - 附加治理元数据
        
        Args:
            proposal_id: 提案 ID
            reviewer_id: 审核者 ID
            reason: 批准原因
        
        Raises:
            ValueError: 如果提案不存在或状态无效
        """
        proposal = self.ingress_service.get_proposal(proposal_id)
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        if not proposal.can_transition_to(ProposalStatus.APPROVED):
            raise ValueError(
                f"Proposal {proposal_id} cannot be approved from status {proposal.status.value}"
            )
        
        # 更新提案状态
        approval_id = f"approval_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}"
        proposal.status = ProposalStatus.APPROVED
        proposal.reviewed_at = datetime.now()
        proposal.reviewer_id = reviewer_id
        proposal.approval_id = approval_id
        
        # 保存提案更新
        self._update_proposal(proposal)
        
        # 注册能力到 Registry（唯一允许的写入路径）
        self._register_capability(proposal, approval_id, reviewer_id)
        
        # 设置生命周期状态为 ACTIVE
        if self.lifecycle_service:
            self.lifecycle_service.state_machine.transition(
                capability_id=proposal.capability_spec.id,
                new_state=CapabilityState.ACTIVE,
                changed_by=reviewer_id,
                proposal_id=proposal_id,
                reason=f"Approved via proposal {proposal_id}: {reason}",
                metadata={
                    "approval_id": approval_id,
                    "source": proposal.source.value,
                    "submitted_by": proposal.submitted_by
                }
            )
        
        # 记录审计事件
        if self.audit_log:
            event = AuditEvent(
                event_id=f"audit_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
                event_type=AuditEventType.PROPOSAL_APPROVED,
                capability_id=proposal.capability_spec.id,
                timestamp=datetime.now(),
                actor=reviewer_id,
                proposal_id=proposal_id,
                signal_ids=[],
                reason=reason or f"Approved proposal {proposal_id}",
                metadata={
                    "approval_id": approval_id,
                    "source": proposal.source.value,
                    "risk_summary": proposal.risk_summary
                }
            )
            self.audit_log.append(event)
    
    def reject_proposal(
        self,
        proposal_id: str,
        reviewer_id: str,
        rejection_reason: str
    ) -> None:
        """
        POST /governance/capabilities/proposals/{id}/reject
        
        拒绝提案
        
        行为：
        - 能力永远不会进入 Registry
        - 必须记录拒绝原因
        
        Args:
            proposal_id: 提案 ID
            reviewer_id: 审核者 ID
            rejection_reason: 拒绝原因（必需）
        
        Raises:
            ValueError: 如果提案不存在或状态无效
        """
        if not rejection_reason or not rejection_reason.strip():
            raise ValueError("rejection_reason is required")
        
        proposal = self.ingress_service.get_proposal(proposal_id)
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        if not proposal.can_transition_to(ProposalStatus.REJECTED):
            raise ValueError(
                f"Proposal {proposal_id} cannot be rejected from status {proposal.status.value}"
            )
        
        # 更新提案状态
        proposal.status = ProposalStatus.REJECTED
        proposal.reviewed_at = datetime.now()
        proposal.reviewer_id = reviewer_id
        proposal.rejection_reason = rejection_reason
        
        # 保存提案更新
        self._update_proposal(proposal)
        
        # 记录审计事件
        if self.audit_log:
            event = AuditEvent(
                event_id=f"audit_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
                event_type=AuditEventType.PROPOSAL_REJECTED,
                capability_id=proposal.capability_spec.id,
                timestamp=datetime.now(),
                actor=reviewer_id,
                proposal_id=proposal_id,
                signal_ids=[],
                reason=rejection_reason,
                metadata={
                    "source": proposal.source.value,
                    "risk_summary": proposal.risk_summary
                }
            )
            self.audit_log.append(event)
    
    def _register_capability(
        self,
        proposal: CapabilityProposal,
        approval_id: str,
        reviewer_id: str
    ):
        """
        注册能力到 Registry（唯一允许的写入路径）
        
        这是唯一可以写入 Registry 的地方。
        
        Args:
            proposal: 已批准的提案
            approval_id: 批准 ID
            reviewer_id: 审核者 ID
        """
        spec = proposal.capability_spec
        
        # 创建 Handler（如果存在）
        # 注意：这里假设 Handler 已经通过其他方式创建（例如 AutoForge）
        # 如果不存在，需要动态加载或创建
        
        # 将 spec 转换为 Registry 需要的格式
        spec_dict = spec.model_dump(mode='json')
        
        # 附加治理元数据
        spec_dict['_governance'] = {
            'approval_id': approval_id,
            'reviewer_id': reviewer_id,
            'approved_at': datetime.now().isoformat(),
            'source': proposal.source.value,
            'proposal_id': proposal.proposal_id
        }
        
        # 注册到 Registry（使用内部方法，因为这是治理批准的路径）
        # 注意：Registry 应该提供 `register_governance_approved` 方法
        # 而不是通用的 `register` 方法
        try:
            # 尝试使用治理批准的注册方法
            if hasattr(self.registry, 'register_governance_approved'):
                self.registry.register_governance_approved(
                    capability_id=spec.id,
                    spec_dict=spec_dict,
                    approval_id=approval_id
                )
            else:
                # 回退到标准注册（但应该被限制）
                self.registry.register(spec.id, None, spec_dict)  # handler 为 None，需要后续加载
        except Exception as e:
            raise RuntimeError(
                f"Failed to register capability {spec.id} to registry: {e}. "
                f"This should only happen through governance approval."
            ) from e
    
    def _update_proposal(self, proposal: CapabilityProposal):
        """更新提案状态"""
        with sqlite3.connect(str(self.ingress_service.db_path)) as conn:
            conn.execute("""
                UPDATE capability_proposals
                SET status = ?, reviewed_at = ?, reviewer_id = ?,
                    rejection_reason = ?, approval_id = ?
                WHERE proposal_id = ?
            """, (
                proposal.status.value,
                proposal.reviewed_at.isoformat() if proposal.reviewed_at else None,
                proposal.reviewer_id,
                proposal.rejection_reason,
                proposal.approval_id,
                proposal.proposal_id
            ))
            conn.commit()
