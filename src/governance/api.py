"""
Governance Platform API - 平台级治理主权 API

这是给系统 / Agent / 未来生态调用的 API，不是 UI。

API 门面，暴露以下方法：
- POST /governance/signals
- POST /governance/evaluate
- POST /governance/lifecycle/freeze
- GET  /governance/lifecycle/{capability_id}
- GET  /governance/audit/events
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from .signals.signal_bus import SignalBus
from .signals.models import SignalType, SignalSeverity, SignalSource
from .evaluation.health_authority import HealthAuthority
from .evaluation.proposal import GovernanceProposal, ProposalStatus
from .lifecycle.lifecycle_service import LifecycleService
from .lifecycle.state_machine import LifecycleStateMachine, CapabilityState
from .audit.audit_log import AuditLog, AuditEvent, AuditEventType


class GovernanceAPI:
    """
    Governance Platform API - 平台级治理主权 API
    
    这是 Runtime 的"宪法法院"。
    
    哲学：
    - Proposal ≠ Execution
    - 事实 ≠ 判断
    - 没有治理 API，AI-First 只是工具；有了它，才是秩序系统
    """
    
    def __init__(
        self,
        signal_bus: Optional[SignalBus] = None,
        health_authority: Optional[HealthAuthority] = None,
        lifecycle_service: Optional[LifecycleService] = None,
        audit_log: Optional[AuditLog] = None
    ):
        """
        初始化 Governance API
        
        Args:
            signal_bus: SignalBus 实例（默认创建）
            health_authority: HealthAuthority 实例（默认创建）
            lifecycle_service: LifecycleService 实例（默认创建）
            audit_log: AuditLog 实例（默认创建）
        """
        self.signal_bus = signal_bus or SignalBus()
        
        if health_authority is None:
            health_authority = HealthAuthority(self.signal_bus)
        self.health_authority = health_authority
        
        if lifecycle_service is None:
            state_machine = LifecycleStateMachine()
            lifecycle_service = LifecycleService(state_machine, self.signal_bus)
        self.lifecycle_service = lifecycle_service
        
        self.audit_log = audit_log or AuditLog()
    
    # ==================== Signal Ingestion API ====================
    
    def append_signal(
        self,
        capability_id: str,
        signal_type: SignalType,
        severity: SignalSeverity,
        source: SignalSource,
        workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        POST /governance/signals
        
        追加 Signal（只记录事实，不判断）
        
        Args:
            capability_id: 能力 ID
            signal_type: 信号类型
            severity: 严重程度
            source: 信号来源
            workflow_id: 工作流 ID
            metadata: 元数据
        
        Returns:
            signal_id: 生成的信号 ID
        """
        return self.signal_bus.append(
            capability_id=capability_id,
            signal_type=signal_type,
            severity=severity,
            source=source,
            workflow_id=workflow_id,
            metadata=metadata
        )
    
    # ==================== Evaluation API ====================
    
    def evaluate(
        self,
        capability_id: str,
        window_hours: int = 24
    ) -> List[GovernanceProposal]:
        """
        POST /governance/evaluate
        
        评估能力并生成 Proposal（只建议，不执行）
        
        Args:
            capability_id: 能力 ID
            window_hours: 评估时间窗口
        
        Returns:
            Proposal 列表
        """
        return self.health_authority.evaluate(capability_id, window_hours)
    
    # ==================== Lifecycle Authority API ====================
    
    def freeze_capability(
        self,
        capability_id: str,
        proposal_id: Optional[str],
        approved_by: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        POST /governance/lifecycle/freeze
        
        冻结能力（主权执行）
        
        Args:
            capability_id: 能力 ID
            proposal_id: 关联的 Proposal ID
            approved_by: 批准者
            reason: 原因
            metadata: 元数据
        """
        # 执行冻结
        self.lifecycle_service.freeze(
            capability_id=capability_id,
            proposal_id=proposal_id,
            approved_by=approved_by,
            reason=reason,
            metadata=metadata
        )
        
        # 记录审计事件
        event = AuditEvent(
            event_id=f"audit_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
            event_type=AuditEventType.CAPABILITY_FROZEN,
            capability_id=capability_id,
            timestamp=datetime.now(),
            actor=approved_by,
            proposal_id=proposal_id,
            signal_ids=[],  # 可以从 Proposal 中获取
            reason=reason,
            metadata=metadata or {}
        )
        self.audit_log.append(event)
    
    def get_lifecycle_state(
        self,
        capability_id: str
    ) -> Dict[str, Any]:
        """
        GET /governance/lifecycle/{capability_id}
        
        获取能力生命周期状态
        
        Args:
            capability_id: 能力 ID
        
        Returns:
            状态信息字典
        """
        state = self.lifecycle_service.get_state(capability_id)
        is_executable = self.lifecycle_service.is_executable(capability_id)
        
        return {
            "capability_id": capability_id,
            "state": state.value,
            "is_executable": is_executable
        }
    
    # ==================== Audit API ====================
    
    def get_audit_events(
        self,
        capability_id: Optional[str] = None,
        proposal_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[AuditEvent]:
        """
        GET /governance/audit/events
        
        获取审计事件
        
        Args:
            capability_id: 可选的能力 ID 过滤
            proposal_id: 可选的 Proposal ID 过滤
            limit: 最大返回数量
        
        Returns:
            审计事件列表
        """
        if capability_id:
            return self.audit_log.get_by_capability(capability_id, limit)
        elif proposal_id:
            return self.audit_log.get_by_proposal(proposal_id)
        else:
            # 返回所有事件（限制数量）
            # 注意：实际实现可能需要分页
            return self.audit_log.get_by_capability("", limit) if limit else []
    
    # ==================== Proposal Management ====================
    
    def approve_proposal(
        self,
        proposal_id: str,
        approved_by: str,
        reason: str
    ) -> None:
        """
        批准 Proposal 并执行
        
        Args:
            proposal_id: Proposal ID
            approved_by: 批准者
            reason: 原因
        """
        # 获取 Proposal
        proposals = self.health_authority.get_pending_proposals()
        proposal = next((p for p in proposals if p.proposal_id == proposal_id), None)
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found or not pending")
        
        # 更新 Proposal 状态
        self.health_authority.update_proposal_status(
            proposal_id=proposal_id,
            status=ProposalStatus.APPROVED,
            reason=f"Approved by {approved_by}: {reason}"
        )
        
        # 根据 Proposal 类型执行
        if proposal.proposal_type == "FREEZE":
            self.freeze_capability(
                capability_id=proposal.capability_id,
                proposal_id=proposal_id,
                approved_by=approved_by,
                reason=reason,
                metadata={"proposal_type": proposal.proposal_type.value}
            )
        elif proposal.proposal_type == "UPGRADE_RISK":
            # 转换到 DEGRADING
            self.lifecycle_service.transition_to_degrading(
                capability_id=proposal.capability_id,
                proposal_id=proposal_id,
                approved_by=approved_by,
                reason=reason
            )
        
        # 记录审计事件
        event = AuditEvent(
            event_id=f"audit_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
            event_type=AuditEventType.PROPOSAL_APPROVED,
            capability_id=proposal.capability_id,
            timestamp=datetime.now(),
            actor=approved_by,
            proposal_id=proposal_id,
            signal_ids=proposal.evidence_signal_ids,
            reason=reason,
            metadata={"proposal_type": proposal.proposal_type.value}
        )
        self.audit_log.append(event)
    
    def reject_proposal(
        self,
        proposal_id: str,
        rejected_by: str,
        reason: str
    ) -> None:
        """
        拒绝 Proposal
        
        Args:
            proposal_id: Proposal ID
            rejected_by: 拒绝者
            reason: 原因
        """
        # 获取 Proposal
        proposals = self.health_authority.get_pending_proposals()
        proposal = next((p for p in proposals if p.proposal_id == proposal_id), None)
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found or not pending")
        
        # 更新 Proposal 状态
        self.health_authority.update_proposal_status(
            proposal_id=proposal_id,
            status=ProposalStatus.REJECTED,
            reason=f"Rejected by {rejected_by}: {reason}"
        )
        
        # 记录审计事件
        event = AuditEvent(
            event_id=f"audit_{datetime.now().timestamp()}_{uuid.uuid4().hex[:8]}",
            event_type=AuditEventType.PROPOSAL_REJECTED,
            capability_id=proposal.capability_id,
            timestamp=datetime.now(),
            actor=rejected_by,
            proposal_id=proposal_id,
            signal_ids=proposal.evidence_signal_ids,
            reason=reason,
            metadata={}
        )
        self.audit_log.append(event)
