"""
Lifecycle Service - 生命周期服务（主权执行层）

唯一允许改变 Capability 状态的模块。
"""

from typing import Optional, Dict
from pathlib import Path

from .state_machine import LifecycleStateMachine, CapabilityState, StateTransitionError
from ..signals.signal_bus import SignalBus
from ..signals.models import SignalType, SignalSeverity, SignalSource


class LifecycleService:
    """
    Lifecycle Service - 主权执行层
    
    职责：
    - 唯一可以改变 Capability 状态的组件
    - 执行 Governance Proposal
    - 发出生命周期变更信号
    
    禁止事项：
    - ❌ 不能由其他组件直接调用（除了 Governance API）
    """
    
    def __init__(
        self,
        state_machine: LifecycleStateMachine,
        signal_bus: SignalBus
    ):
        """
        初始化 Lifecycle Service
        
        Args:
            state_machine: 状态机实例
            signal_bus: Signal Bus 实例（用于发出信号）
        """
        self.state_machine = state_machine
        self.signal_bus = signal_bus
    
    def get_state(self, capability_id: str) -> CapabilityState:
        """
        获取能力状态
        
        Args:
            capability_id: 能力 ID
        
        Returns:
            当前状态
        """
        return self.state_machine.get_state(capability_id)
    
    def freeze(
        self,
        capability_id: str,
        proposal_id: Optional[str],
        approved_by: str,
        reason: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        冻结能力
        
        Args:
            capability_id: 能力 ID
            proposal_id: 关联的 Proposal ID（如果有）
            approved_by: 批准者
            reason: 原因
            metadata: 元数据
        
        Raises:
            StateTransitionError: 如果转换不合法
        """
        current_state = self.get_state(capability_id)
        
        # 如果已经是 FROZEN，不需要再次转换
        if current_state == CapabilityState.FROZEN:
            return
        
        self.state_machine.transition(
            capability_id=capability_id,
            new_state=CapabilityState.FROZEN,
            changed_by=approved_by,
            proposal_id=proposal_id,
            reason=reason,
            metadata=metadata
        )
        
        # 发出生命周期变更信号
        self.signal_bus.append(
            capability_id=capability_id,
            signal_type=SignalType.LIFECYCLE_CHANGED,
            severity=SignalSeverity.HIGH,
            source=SignalSource.GOVERNANCE,
            metadata={
                "new_state": CapabilityState.FROZEN.value,
                "proposal_id": proposal_id,
                "approved_by": approved_by,
                "reason": reason,
                **(metadata or {})
            }
        )
    
    def unfreeze(
        self,
        capability_id: str,
        approved_by: str,
        reason: str
    ) -> None:
        """
        解冻能力
        
        Args:
            capability_id: 能力 ID
            approved_by: 批准者
            reason: 原因
        """
        current_state = self.get_state(capability_id)
        if current_state != CapabilityState.FROZEN:
            raise StateTransitionError(
                f"Cannot unfreeze capability {capability_id} in state {current_state.value}"
            )
        
        self.state_machine.transition(
            capability_id=capability_id,
            new_state=CapabilityState.ACTIVE,
            changed_by=approved_by,
            reason=reason
        )
        
        # 发出生命周期变更信号
        self.signal_bus.append(
            capability_id=capability_id,
            signal_type=SignalType.LIFECYCLE_CHANGED,
            severity=SignalSeverity.MEDIUM,
            source=SignalSource.GOVERNANCE,
            metadata={
                "new_state": CapabilityState.ACTIVE.value,
                "approved_by": approved_by,
                "reason": reason
            }
        )
    
    def transition_to_degrading(
        self,
        capability_id: str,
        proposal_id: Optional[str],
        approved_by: str,
        reason: str
    ) -> None:
        """
        转换到 DEGRADING 状态
        
        Args:
            capability_id: 能力 ID
            proposal_id: 关联的 Proposal ID
            approved_by: 批准者
            reason: 原因
        """
        self.state_machine.transition(
            capability_id=capability_id,
            new_state=CapabilityState.DEGRADING,
            changed_by=approved_by,
            proposal_id=proposal_id,
            reason=reason
        )
        
        # 发出信号
        self.signal_bus.append(
            capability_id=capability_id,
            signal_type=SignalType.HEALTH_DEGRADED,
            severity=SignalSeverity.MEDIUM,
            source=SignalSource.GOVERNANCE,
            metadata={
                "new_state": CapabilityState.DEGRADING.value,
                "proposal_id": proposal_id,
                "approved_by": approved_by
            }
        )
    
    def is_executable(self, capability_id: str) -> bool:
        """
        检查能力是否可执行
        
        FROZEN 和 DEPRECATED 状态不可执行。
        
        Args:
            capability_id: 能力 ID
        
        Returns:
            是否可执行
        """
        state = self.get_state(capability_id)
        return state not in {CapabilityState.FROZEN, CapabilityState.DEPRECATED}
