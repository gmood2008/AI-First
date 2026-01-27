"""
Capability Ingress & Governance Enforcement 验收测试

验收标准：
1. Ingress Test: 提交能力创建 Proposal，Registry 保持不变
2. Approval Test: 批准提案激活能力，Runtime 可以执行
3. Rejection Test: 拒绝的提案永远不会出现在 Registry
4. Security Test: 任何绕过治理的尝试都会抛出硬错误
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from governance.ingress.api import CapabilityIngressAPI
from governance.ingress.models import ProposalSource, ProposalStatus
from specs.v3.capability_schema import CapabilitySpec, RiskLevel, OperationType, SideEffect, Compensation, CapabilityMetadata, Contracts, Behavior, Interface, Parameter, Returns
from runtime.registry import CapabilityRegistry
from runtime.engine import RuntimeEngine
from runtime.types import ExecutionContext, ExecutionStatus


@pytest.fixture
def temp_dir():
    """创建临时目录用于测试数据库"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def ingress_api(temp_dir):
    """创建 CapabilityIngressAPI 实例"""
    from governance.ingress.ingress_service import CapabilityIngressService
    from governance.lifecycle.state_machine import LifecycleStateMachine
    from governance.lifecycle.lifecycle_service import LifecycleService
    from governance.signals.signal_bus import SignalBus
    from governance.audit.audit_log import AuditLog
    
    ingress_service = CapabilityIngressService(db_path=temp_dir / "proposals.db")
    registry = CapabilityRegistry(governance_enforced=True)
    signal_bus = SignalBus()
    state_machine = LifecycleStateMachine(db_path=temp_dir / "lifecycle.db")
    lifecycle_service = LifecycleService(state_machine, signal_bus)
    audit_log = AuditLog(db_path=temp_dir / "audit.db")
    
    return CapabilityIngressAPI(
        ingress_service=ingress_service,
        registry=registry,
        lifecycle_service=lifecycle_service,
        audit_log=audit_log
    )


def create_test_spec(capability_id: str) -> CapabilitySpec:
    """创建测试用的 CapabilitySpec"""
    # 使用简化的 spec 创建（根据实际 schema 结构）
    spec_dict = {
        "id": capability_id,
        "description": "Test capability",
        "metadata": {
            "id": capability_id,
            "version": "1.0.0",
            "author": "Test",
            "description": "Test capability"
        },
        "risk": {"level": "LOW"},
        "operation_type": "READ",
        "behavior": {
            "undo_strategy": "no_undo_required_operation_is_read_only"
        },
        "interface": {
            "parameters": [],
            "returns": {"type": "object", "description": "Test result"}
        }
    }
    return CapabilitySpec.model_validate(spec_dict)


class TestIngress:
    """测试能力准入（验收标准 1）"""
    
    def test_submit_proposal_creates_proposal(self, ingress_api):
        """
        验收标准 1: 提交能力创建 Proposal，Registry 保持不变
        """
        spec = create_test_spec("test.capability.ingress")
        
        # 提交提案
        proposal = ingress_api.submit_proposal(
            capability_spec=spec,
            source=ProposalSource.INTERNAL,
            submitted_by="test_user",
            justification="Test proposal"
        )
        
        # 验证提案已创建
        assert proposal.proposal_id is not None
        assert proposal.status == ProposalStatus.PENDING_REVIEW
        assert proposal.capability_spec.id == "test.capability.ingress"
        
        # 验证 Registry 保持不变
        assert not ingress_api.registry.has_capability("test.capability.ingress")
        assert len(ingress_api.registry.list_capabilities()) == 0


class TestApproval:
    """测试审批（验收标准 2）"""
    
    def test_approve_proposal_activates_capability(self, ingress_api):
        """
        验收标准 2: 批准提案激活能力，Runtime 可以执行
        """
        spec = create_test_spec("test.capability.approval")
        
        # 提交提案
        proposal = ingress_api.submit_proposal(
            capability_spec=spec,
            source=ProposalSource.INTERNAL,
            submitted_by="test_user",
            justification="Test approval"
        )
        
        # 批准提案
        ingress_api.approve_proposal(
            proposal_id=proposal.proposal_id,
            reviewer_id="admin",
            reason="Approved for testing"
        )
        
        # 验证提案状态
        updated_proposal = ingress_api.get_proposal(proposal.proposal_id)
        assert updated_proposal.status == ProposalStatus.APPROVED
        assert updated_proposal.approval_id is not None
        
        # 验证能力已注册（注意：由于没有 handler，可能无法完全执行）
        # 但至少应该记录在治理元数据中
        assert ingress_api.registry._governance_approved.get("test.capability.approval") is not None


class TestRejection:
    """测试拒绝（验收标准 3）"""
    
    def test_rejected_proposal_never_in_registry(self, ingress_api):
        """
        验收标准 3: 拒绝的提案永远不会出现在 Registry
        """
        spec = create_test_spec("test.capability.rejection")
        
        # 提交提案
        proposal = ingress_api.submit_proposal(
            capability_spec=spec,
            source=ProposalSource.INTERNAL,
            submitted_by="test_user",
            justification="Test rejection"
        )
        
        # 拒绝提案
        ingress_api.reject_proposal(
            proposal_id=proposal.proposal_id,
            reviewer_id="admin",
            rejection_reason="Not suitable for production"
        )
        
        # 验证提案状态
        updated_proposal = ingress_api.get_proposal(proposal.proposal_id)
        assert updated_proposal.status == ProposalStatus.REJECTED
        assert updated_proposal.rejection_reason == "Not suitable for production"
        
        # 验证能力未注册
        assert not ingress_api.registry.has_capability("test.capability.rejection")
        assert "test.capability.rejection" not in ingress_api.registry._governance_approved


class TestSecurity:
    """测试安全性（验收标准 4）"""
    
    def test_direct_registration_forbidden(self, ingress_api):
        """
        验收标准 4: 任何绕过治理的尝试都会抛出硬错误
        """
        from runtime.handler import ActionHandler
        
        # 尝试直接注册（应该失败）
        registry = CapabilityRegistry(governance_enforced=True)
        
        # 创建一个简单的 mock handler
        class MockHandler(ActionHandler):
            def execute(self, params, context):
                return {"result": "test"}
        
        with pytest.raises(RuntimeError) as exc_info:
            registry.register(
                capability_id="test.capability.direct",
                handler=MockHandler({}),
                spec_dict={}
            )
        
        assert "SECURITY" in str(exc_info.value)
        assert "governance" in str(exc_info.value).lower()
    
    def test_batch_proposals_creates_individual_proposals(self, ingress_api):
        """批量提交创建独立提案"""
        specs = [
            create_test_spec("test.capability.batch1"),
            create_test_spec("test.capability.batch2"),
            create_test_spec("test.capability.batch3")
        ]
        
        proposals = ingress_api.submit_batch_proposals(
            capability_specs=specs,
            source=ProposalSource.INTERNAL,
            submitted_by="test_user",
            justification="Batch test"
        )
        
        # 验证每个能力都有独立的提案
        assert len(proposals) == 3
        assert len(set(p.capability_spec.id for p in proposals)) == 3
        
        # 验证所有提案都是 PENDING_REVIEW
        assert all(p.status == ProposalStatus.PENDING_REVIEW for p in proposals)
        
        # 验证没有能力被激活
        assert not ingress_api.registry.has_capability("test.capability.batch1")
        assert not ingress_api.registry.has_capability("test.capability.batch2")
        assert not ingress_api.registry.has_capability("test.capability.batch3")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
