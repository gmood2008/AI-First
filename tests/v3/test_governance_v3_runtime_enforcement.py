"""
Governance v3 Runtime Enforcement 验收测试

验收标准：
1. 冻结 Capability → Runtime 立即拒绝执行
2. Proposal 审批 → 状态正确变更
3. 每个决策 → GDR 可查询
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from governance.api_v3 import GovernanceAPIV3
from governance.decision_room.proposal_model import ProposalTypeV2
from governance.signals.models import SignalType, SignalSeverity, SignalSource
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
def governance_api_v3(temp_dir):
    """创建 GovernanceAPIV3 实例"""
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
    
    return GovernanceAPIV3(
        health_authority=health_authority,
        lifecycle_service=lifecycle_service,
        signal_bus=signal_bus
    )


class TestRuntimeEnforcement:
    """测试 Runtime Enforcement（验收标准 1）"""
    
    def test_frozen_capability_rejected_immediately(self, governance_api_v3):
        """
        验收标准 1: 冻结 Capability → Runtime 立即拒绝执行
        
        这是 v3 是否成功的生死线。
        """
        capability_id = "test.capability.frozen"
        
        # 创建并批准 FREEZE 提案
        proposal = governance_api_v3.platform_api.v2_decision_room.proposal_lifecycle_api.create_proposal(
            proposal_type=ProposalTypeV2.FREEZE,
            target_capability_id=capability_id,
            triggering_evidence={"signals": ["sig_1"]},
            created_by="system"
        )
        
        # 批准提案
        decision = governance_api_v3.approve_proposal(
            proposal_id=proposal.proposal_id,
            decided_by="admin",
            rationale="Security concern"
        )
        
        # 验证能力已冻结
        lifecycle = governance_api_v3.get_capability_lifecycle(capability_id)
        assert lifecycle["current_state"] == "FROZEN"
        assert not lifecycle["is_executable"]
        
        # Runtime 尝试执行（应该被立即拒绝）
        registry = CapabilityRegistry()
        engine = RuntimeEngine(
            registry=registry,
            lifecycle_service=governance_api_v3.lifecycle_service,
            signal_bus=governance_api_v3.signal_bus
        )
        
        context = ExecutionContext(
            user_id="test_user",
            workspace_root=Path("/tmp/test"),
            session_id="test_session",
            confirmation_callback=None,
            undo_enabled=False
        )
        
        result = engine.execute(capability_id, {}, context)
        
        # 必须返回明确错误码（非异常）
        assert result.status == ExecutionStatus.ERROR
        assert "FROZEN" in result.error_message or "cannot be executed" in result.error_message
        
        print(f"✅ Runtime 立即拒绝执行: {result.error_message}")


class TestProposalApproval:
    """测试提案审批（验收标准 2）"""
    
    def test_proposal_approval_changes_state(self, governance_api_v3):
        """
        验收标准 2: Proposal 审批 → 状态正确变更
        """
        capability_id = "test.capability.approval"
        
        # 创建 FREEZE 提案
        proposal = governance_api_v3.platform_api.v2_decision_room.proposal_lifecycle_api.create_proposal(
            proposal_type=ProposalTypeV2.FREEZE,
            target_capability_id=capability_id,
            triggering_evidence={"signals": ["sig_1"]},
            created_by="system"
        )
        
        # 验证提案状态为 PENDING
        proposal_detail = governance_api_v3.get_proposal(proposal.proposal_id)
        assert proposal_detail["status"] == "PENDING"
        
        # 批准提案
        decision = governance_api_v3.approve_proposal(
            proposal_id=proposal.proposal_id,
            decided_by="admin",
            rationale="Approved after review"
        )
        
        # 验证提案状态已变更
        updated_proposal = governance_api_v3.get_proposal(proposal.proposal_id)
        assert updated_proposal["status"] == "APPROVED"
        
        # 验证能力状态已变更
        lifecycle = governance_api_v3.get_capability_lifecycle(capability_id)
        assert lifecycle["current_state"] == "FROZEN"
        
        print(f"✅ 提案审批成功，状态已变更: {decision['decision_id']}")


class TestGDRQuery:
    """测试 GDR 查询（验收标准 3）"""
    
    def test_every_decision_creates_queryable_gdr(self, governance_api_v3):
        """
        验收标准 3: 每个决策 → GDR 可查询
        """
        capability_id = "test.capability.gdr"
        
        # 创建并批准提案
        proposal = governance_api_v3.platform_api.v2_decision_room.proposal_lifecycle_api.create_proposal(
            proposal_type=ProposalTypeV2.FREEZE,
            target_capability_id=capability_id,
            triggering_evidence={"signals": ["sig_1"]},
            created_by="system"
        )
        
        decision = governance_api_v3.approve_proposal(
            proposal_id=proposal.proposal_id,
            decided_by="admin",
            rationale="Test GDR"
        )
        
        decision_id = decision["decision_id"]
        
        # 查询 GDR
        gdr = governance_api_v3.get_decision(decision_id)
        
        assert gdr is not None
        assert gdr["decision_id"] == decision_id
        assert gdr["proposal_id"] == proposal.proposal_id
        assert gdr["decision"] == "APPROVE"
        assert gdr["decided_by"] == "admin"
        assert gdr["rationale"] == "Test GDR"
        assert capability_id in gdr["affected_capabilities"]
        assert gdr["resulting_state_transition"] is not None
        
        print(f"✅ GDR 可查询: {gdr['decision_id']}")


class TestAPISovereignty:
    """测试 API 主权"""
    
    def test_all_logic_in_api(self, governance_api_v3):
        """验证所有逻辑都在 API 层"""
        capability_id = "test.capability.api"
        
        # 添加信号
        governance_api_v3.signal_bus.append(
            capability_id=capability_id,
            signal_type=SignalType.EXECUTION_FAILED,
            severity=SignalSeverity.HIGH,
            source=SignalSource.RUNTIME
        )
        
        # 获取健康度（由 API 计算）
        health = governance_api_v3.get_capability_health(capability_id)
        
        assert "reliability_score" in health
        assert "friction_score" in health
        assert "current_state" in health
        
        # 获取信号（由 API 提供）
        signals = governance_api_v3.get_capability_signals(capability_id)
        assert len(signals) > 0
        
        # 获取生命周期（由 API 提供）
        lifecycle = governance_api_v3.get_capability_lifecycle(capability_id)
        assert "current_state" in lifecycle
        assert "is_executable" in lifecycle
        
        print("✅ 所有逻辑都在 API 层")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
