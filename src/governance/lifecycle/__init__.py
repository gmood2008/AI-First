"""
Domain C: Lifecycle Authority API (主权执行层)

唯一允许改变 Capability 状态的模块。
Runtime 在执行前必须查询此状态。
"""

from .state_machine import LifecycleStateMachine, CapabilityState, StateTransitionError
from .lifecycle_service import LifecycleService
from .enforcement import GovernanceViolation, enforce_lifecycle_state

__all__ = [
    "LifecycleStateMachine",
    "CapabilityState",
    "StateTransitionError",
    "LifecycleService",
    "GovernanceViolation",
    "enforce_lifecycle_state",
]
