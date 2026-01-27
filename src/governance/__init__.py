"""
AI-First Governance Platform API - 平台级治理主权 API

这是 Runtime 的"宪法法院"。

哲学：
- Proposal ≠ Execution
- 事实 ≠ 判断
- 没有治理 API，AI-First 只是工具；有了它，才是秩序系统
"""

# Domain A: Signal Ingestion (事实层)
from .signals import (
    Signal, SignalType, SignalSeverity, SignalSource,
    SignalBus, SignalRepository
)

# Domain B: Governance Evaluation (裁决生成层)
from .evaluation import (
    GovernanceProposal, ProposalType, ProposalStatus,
    HealthAuthority, EvaluationRules
)

# Domain C: Lifecycle Authority (主权执行层)
from .lifecycle import (
    LifecycleStateMachine, CapabilityState, StateTransitionError,
    LifecycleService,
    GovernanceViolation, enforce_lifecycle_state
)

# Domain D: Governance Audit (治理账本)
from .audit import (
    AuditLog, AuditEvent, AuditEventType,
    AuditQueries
)

# Platform API
from .api import GovernanceAPI

__all__ = [
    # Domain A
    "Signal",
    "SignalType",
    "SignalSeverity",
    "SignalSource",
    "SignalBus",
    "SignalRepository",
    # Domain B
    "GovernanceProposal",
    "ProposalType",
    "ProposalStatus",
    "HealthAuthority",
    "EvaluationRules",
    # Domain C
    "LifecycleStateMachine",
    "CapabilityState",
    "StateTransitionError",
    "LifecycleService",
    "GovernanceViolation",
    "enforce_lifecycle_state",
    # Domain D
    "AuditLog",
    "AuditEvent",
    "AuditEventType",
    "AuditQueries",
    # Platform API
    "GovernanceAPI",
]
