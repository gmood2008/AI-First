"""
Lifecycle Enforcement - 生命周期强制执行

Runtime 在执行前必须查询此状态。
如果状态是 FROZEN 或 DEPRECATED，必须立刻拒绝执行。
"""

from .state_machine import CapabilityState
from .lifecycle_service import LifecycleService


class GovernanceViolation(Exception):
    """
    治理违规异常
    
    当 Runtime 尝试执行 FROZEN 或 DEPRECATED 能力时抛出。
    """
    pass


def enforce_lifecycle_state(
    lifecycle_service: LifecycleService,
    capability_id: str
) -> None:
    """
    强制执行生命周期状态检查
    
    Runtime 在执行前必须调用此函数。
    如果能力是 FROZEN 或 DEPRECATED，抛出 GovernanceViolation。
    
    Args:
        lifecycle_service: LifecycleService 实例
        capability_id: 能力 ID
    
    Raises:
        GovernanceViolation: 如果能力不可执行
    """
    if not lifecycle_service.is_executable(capability_id):
        state = lifecycle_service.get_state(capability_id)
        raise GovernanceViolation(
            f"Capability {capability_id} is {state.value} and cannot be executed. "
            f"This is a governance decision and cannot be overridden."
        )
