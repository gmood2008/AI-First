"""
Governance Platform V1 + V2 API 验收测试

验收标准：
1. Signal → Proposal: 模拟重复失败，HealthAuthority 生成 FIX proposal
2. Proposal → Decision: 批准 FREEZE，GDR 创建
3. Decision → Runtime Enforcement: 冻结的能力在执行时被拒绝
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from governance.platform_api import GovernancePlatformAPI
from governance.signals.models import SignalType, SignalSeverity, SignalSource
from governance.decision_room.proposal_model import ProposalTypeV2, ProposalStatusV2
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
def platform_api(temp_dir):
    """创建 GovernancePlatformAPI 实例"""
    from governance.signals.repository import SignalRepository
    from governance.signals.signal_bus import SignalBus
    from governance.evaluation.health_authority import HealthAuthority
    from governance.lifecycle.state_machine import LifecycleStateMachine
    from governance.lifecycle.lifecycle_service import LifecycleService
    
    signal_repo = SignalRepository(db_path=temp_dir / "signals.db")
    signal_bus = SignalBus(repository=signal_repo)
    health_authority = HealthAuthority(signal_bus, db_path=temp_dir / "proposals.db")
    state_machine = LifecycleStateMachine(db_path=temp_dir / "lifecycle.db")
    lifecycle_service = LifecycleService(state_machine, signal_bus)
    
    return GovernancePlatformAPI(
        health_authority=health_authority,
        lifecycle_service=lifecycle_service,
        signal_bus=signal_bus
    )


class TestSignalToProposal:
    """测试 Signal → Proposal（验收标准 1）"""
    
    def test_repeated_failures_generate_fix_proposal(self, platform_api):
        """
        验收标准 1: 模拟重复失败，HealthAuthority 生成 FIX proposal
        """
        capability_id = "test.capability.failures"
        
        # 模拟重复失败
        for i in range(10):
            platform_api.signal_bus.append(
                capability_id=capability_id,
                signal_type=SignalType.EXECUTION_FAILED,
                severity=SignalSeverity.HIGH,
                source=SignalSource.RUNTIME
            )
        
        # HealthAuthority 评估并生成 Proposal
        proposals = platform_api.health_authority.evaluate(capability_id, window_hours=24)
        
        # 应该生成 FIX Proposal（因为可靠性低）
        fix_proposals = [p for p in proposals if p.proposal_type.value == "FIX"]
        assert len(fix_proposals) > 0, "应该生成 FIX Proposal"
        
        print(f"✅ 生成了 {len(fix_proposals)} 个 FIX Proposal")


class TestProposalToDecision:
    """测试 Proposal → Decision（验收标准 2）"""
    
    def test_approve_freeze_creates_gdr(self, platform_api):
        """
        验收标准 2: 批准 FREEZE，GDR 创建
        """
        capability_id = "test.capability.freeze"
        
        # 创建 FREEZE 提案
        proposal = platform_api.v2_decision_room.proposal_lifecycle_api.create_proposal(
            proposal_type=ProposalTypeV2.FREEZE,
            target_capability_id=capability_id,
            triggering_evidence={"signals": ["sig_1", "sig_2"]},
            created_by="system"
        )
        
        # 批准提案
        decision_record = platform_api.approve_proposal(
            proposal_id=proposal.proposal_id,
            decided_by="admin",
            rationale="Security concern"
        )
        
        # 验证 GDR 创建
        assert decision_record["decision"] == "APPROVE"
        assert decision_record["proposal_id"] == proposal.proposal_id
        assert decision_record["rationale"] == "Security concern"
        assert decision_record["resulting_state_transition"] is not None
        
        # 验证提案状态
        updated_proposal = platform_api.get_proposal(proposal.proposal_id)
        assert updated_proposal["status"] == ProposalStatusV2.APPROVED.value
        
        print(f"✅ GDR 创建成功: {decision_record['decision_id']}")


class TestDecisionToRuntimeEnforcement:
    """测试 Decision → Runtime Enforcement（验收标准 3）"""
    
    def test_frozen_capability_rejected_at_execution(self, platform_api):
        """
        验收标准 3: 冻结的能力在执行时被拒绝
        """
        capability_id = "test.capability.frozen"
        
        # 创建并批准 FREEZE 提案
        proposal = platform_api.v2_decision_room.proposal_lifecycle_api.create_proposal(
            proposal_type=ProposalTypeV2.FREEZE,
            target_capability_id=capability_id,
            triggering_evidence={"signals": ["sig_1"]},
            created_by="system"
        )
        
        platform_api.approve_proposal(
            proposal_id=proposal.proposal_id,
            decided_by="admin",
            rationale="Test freeze"
        )
        
        # 验证能力已冻结
        state = platform_api.lifecycle_service.get_state(capability_id)
        assert state.value == "FROZEN"
        
        # Runtime 尝试执行（应该被拒绝）
        registry = CapabilityRegistry()
        engine = RuntimeEngine(
            registry=registry,
            lifecycle_service=platform_api.lifecycle_service,
            signal_bus=platform_api.signal_bus
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
        
        print(f"✅ Runtime 拒绝执行: {result.error_message}")


class TestV1Observatory:
    """测试 V1 Observatory APIs（只读）"""
    
    def test_get_capability_health(self, platform_api):
        """测试获取能力健康度"""
        capability_id = "test.capability.health"
        
        # 添加一些信号
        platform_api.signal_bus.append(
            capability_id=capability_id,
            signal_type=SignalType.EXECUTION_SUCCESS,
            severity=SignalSeverity.LOW,
            source=SignalSource.RUNTIME
        )
        
        # 获取健康度
        health = platform_api.get_capability_health(capability_id)
        
        assert health["capability_id"] == capability_id
        assert "reliability_score" in health
        assert "friction_score" in health
        assert "current_state" in health
        
        print(f"✅ 健康度获取成功: {health['reliability_score']:.1f}%")
    
    def test_get_risk_distribution(self, platform_api):
        """测试获取风险分布"""
        distribution = platform_api.get_risk_distribution()
        
        assert "distribution" in distribution
        assert "total" in distribution
        assert "by_risk" in distribution
        
        print(f"✅ 风险分布获取成功: {distribution['total']} 个能力")
    
    def test_get_signals(self, platform_api):
        """测试获取信号"""
        capability_id = "test.capability.signals"
        
        # 添加信号
        platform_api.signal_bus.append(
            capability_id=capability_id,
            signal_type=SignalType.ROLLBACK_TRIGGERED,
            severity=SignalSeverity.HIGH,
            source=SignalSource.WORKFLOW
        )
        
        # 获取信号
        signals = platform_api.get_signals(capability_id=capability_id)
        
        assert len(signals) > 0
        assert signals[0]["capability_id"] == capability_id
        assert signals[0]["signal_type"] == SignalType.ROLLBACK_TRIGGERED.value
        
        print(f"✅ 信号获取成功: {len(signals)} 条")
    
    def test_get_missing_capabilities(self, platform_api):
        """测试获取缺失能力"""
        # 添加 CAPABILITY_NOT_FOUND 信号
        for i in range(5):
            platform_api.signal_bus.append(
                capability_id="missing.capability.1",
                signal_type=SignalType.CAPABILITY_NOT_FOUND,
                severity=SignalSeverity.MEDIUM,
                source=SignalSource.RUNTIME
            )
        
        # 获取缺失能力
        missing = platform_api.get_missing_capabilities(window_hours=24, min_frequency=1)
        
        assert len(missing) > 0
        assert missing[0]["capability_id"] == "missing.capability.1"
        assert missing[0]["frequency"] >= 5
        
        print(f"✅ 缺失能力获取成功: {len(missing)} 个")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
