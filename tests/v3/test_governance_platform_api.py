"""
Governance Platform API 验收测试

强制验收标准：
1. Signal Test: 模拟 workflow rollback → governance_signals 有 ROLLBACK_TRIGGERED
2. Health Test: 注入 10 条失败 signal → HealthAuthority 生成 Proposal(FREEZE)
3. Governance Test: Lifecycle 冻结 capability → Runtime 立即拒绝执行
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from governance.api import GovernanceAPI
from governance.signals.models import SignalType, SignalSeverity, SignalSource
from governance.lifecycle.enforcement import GovernanceViolation
from runtime.engine import RuntimeEngine
from runtime.registry import CapabilityRegistry
from runtime.types import ExecutionContext, ExecutionStatus


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试数据库"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def governance_api(temp_dir):
    """创建 GovernanceAPI 实例"""
    from governance.signals.repository import SignalRepository
    from governance.signals.signal_bus import SignalBus
    from governance.evaluation.health_authority import HealthAuthority
    from governance.lifecycle.state_machine import LifecycleStateMachine
    from governance.lifecycle.lifecycle_service import LifecycleService
    from governance.audit.audit_log import AuditLog
    
    signal_repo = SignalRepository(db_path=temp_dir / "signals.db")
    signal_bus = SignalBus(repository=signal_repo)
    health_authority = HealthAuthority(signal_bus, db_path=temp_dir / "proposals.db")
    state_machine = LifecycleStateMachine(db_path=temp_dir / "lifecycle.db")
    lifecycle_service = LifecycleService(state_machine, signal_bus)
    audit_log = AuditLog(db_path=temp_dir / "audit.db")
    
    return GovernanceAPI(
        signal_bus=signal_bus,
        health_authority=health_authority,
        lifecycle_service=lifecycle_service,
        audit_log=audit_log
    )


class TestSignalIngestion:
    """测试 Signal 摄入（验收标准 1）"""
    
    def test_rollback_signal_recorded(self, governance_api):
        """
        验收标准 1: 模拟 workflow rollback → governance_signals 有 ROLLBACK_TRIGGERED
        """
        capability_id = "test.capability.rollback"
        
        # 模拟 rollback
        signal_id = governance_api.append_signal(
            capability_id=capability_id,
            signal_type=SignalType.ROLLBACK_TRIGGERED,
            severity=SignalSeverity.HIGH,
            source=SignalSource.WORKFLOW,
            metadata={"workflow_id": "wf_123", "reason": "Test rollback"}
        )
        
        # 验证信号已记录
        signals = governance_api.signal_bus.get_signals(
            capability_id=capability_id,
            signal_type=SignalType.ROLLBACK_TRIGGERED
        )
        
        assert len(signals) > 0
        assert signals[0].signal_id == signal_id
        assert signals[0].signal_type == SignalType.ROLLBACK_TRIGGERED
        assert signals[0].source == SignalSource.WORKFLOW


class TestHealthEvaluation:
    """测试健康评估（验收标准 2）"""
    
    def test_10_failures_generate_freeze_proposal(self, governance_api):
        """
        验收标准 2: 注入 10 条失败 signal → HealthAuthority 生成 Proposal(FREEZE)
        """
        capability_id = "test.capability.failures"
        
        # 注入 10 条失败信号
        for i in range(10):
            governance_api.append_signal(
                capability_id=capability_id,
                signal_type=SignalType.EXECUTION_FAILED,
                severity=SignalSeverity.HIGH,
                source=SignalSource.RUNTIME,
                metadata={"attempt": i}
            )
        
        # 评估并生成 Proposal
        proposals = governance_api.evaluate(capability_id, window_hours=24)
        
        # 应该生成 FREEZE Proposal（因为失败率高）
        freeze_proposals = [p for p in proposals if p.proposal_type.value == "FREEZE"]
        assert len(freeze_proposals) > 0, "应该生成 FREEZE Proposal"
        
        # 验证 Proposal 包含证据
        proposal = freeze_proposals[0]
        assert len(proposal.evidence_signal_ids) > 0
        assert proposal.confidence > 0
        assert proposal.reason


class TestGovernanceEnforcement:
    """测试治理强制执行（验收标准 3）"""
    
    def test_frozen_capability_rejected_by_runtime(self, governance_api):
        """
        验收标准 3: Lifecycle 冻结 capability → Runtime 立即拒绝执行
        """
        capability_id = "test.capability.frozen"
        
        # 冻结能力
        governance_api.freeze_capability(
            capability_id=capability_id,
            proposal_id=None,
            approved_by="test_admin",
            reason="Test freeze"
        )
        
        # 验证状态
        state_info = governance_api.get_lifecycle_state(capability_id)
        assert state_info["state"] == "FROZEN"
        assert not state_info["is_executable"]
        
        # Runtime 尝试执行（应该被拒绝）
        registry = CapabilityRegistry()
        engine = RuntimeEngine(
            registry=registry,
            lifecycle_service=governance_api.lifecycle_service,
            signal_bus=governance_api.signal_bus
        )
        
        context = ExecutionContext(
            user_id="test_user",
            workspace_root=Path("/tmp/test"),
            session_id="test_session",
            confirmation_callback=None,
            undo_enabled=False
        )
        
        result = engine.execute(capability_id, {}, context)
        
        # 应该被拒绝
        assert result.status == ExecutionStatus.ERROR
        assert "FROZEN" in result.error_message or "cannot be executed" in result.error_message
        
        # 应该发出 GOVERNANCE_REJECTED 信号
        signals = governance_api.signal_bus.get_signals(
            capability_id=capability_id,
            signal_type=SignalType.GOVERNANCE_REJECTED
        )
        assert len(signals) > 0


class TestGovernanceBoundaries:
    """测试治理边界"""
    
    def test_health_authority_read_only(self, governance_api):
        """HealthAuthority 不能改变能力状态"""
        capability_id = "test.capability.boundary"
        
        # HealthAuthority 只能生成 Proposal
        proposals = governance_api.evaluate(capability_id)
        
        # 状态应该仍然是 ACTIVE（默认）
        state_info = governance_api.get_lifecycle_state(capability_id)
        assert state_info["state"] == "ACTIVE"
        
        # HealthAuthority 不应该有直接改变状态的方法
        assert not hasattr(governance_api.health_authority, 'freeze')
        assert not hasattr(governance_api.health_authority, 'transition')
    
    def test_only_lifecycle_service_can_change_state(self, governance_api):
        """只有 LifecycleService 可以改变状态"""
        capability_id = "test.capability.state_change"
        
        # 初始状态
        state_info = governance_api.get_lifecycle_state(capability_id)
        assert state_info["state"] == "ACTIVE"
        
        # LifecycleService 可以改变状态
        governance_api.freeze_capability(
            capability_id=capability_id,
            proposal_id=None,
            approved_by="test_admin",
            reason="Test"
        )
        
        # 状态已改变
        state_info = governance_api.get_lifecycle_state(capability_id)
        assert state_info["state"] == "FROZEN"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
