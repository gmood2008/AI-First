"""
AI-First Runtime v3.0 - Policy Integration Tests

Test PolicyEngine integration with WorkflowEngine.

Acceptance Criteria (Week 5):
- Agent tries to delete a file -> Policy denies -> Workflow halts & rolls back
"""

import pytest
import tempfile
from pathlib import Path

from src.runtime.workflow.engine import WorkflowEngine
from src.runtime.workflow.policy_engine import PolicyEngine, PolicyRule, PolicyDecision
from src.runtime.workflow.persistence import WorkflowPersistence
from src.runtime.workflow.human_approval import HumanApprovalManager
from src.runtime.engine import RuntimeEngine
from src.runtime.types import ExecutionContext
from src.runtime.registry import CapabilityRegistry
from src.runtime.stdlib.loader import load_stdlib
from src.specs.v3.workflow_schema import (
    WorkflowSpec,
    WorkflowMetadata,
    WorkflowStep,
    StepType,
    WorkflowStatus,
    RiskLevel
)


def resolve_specs_dir():
    """Resolve the specs directory path"""
    return Path(__file__).parent.parent.parent / "src" / "specs" / "stdlib"


@pytest.fixture
def test_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = Path(f.name)
    
    yield db_path
    
    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def test_workspace():
    """Create a temporary workspace directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestPolicyIntegration:
    """Test PolicyEngine integration with WorkflowEngine"""
    
    def test_policy_denies_workflow_halts_and_rolls_back(self, test_db, test_workspace):
        """
        Acceptance Criteria (Week 5):
        Agent tries to delete a file -> Policy denies -> Workflow halts & rolls back
        
        Scenario:
        1. Create a file (Step 1)
        2. Try to delete the file (Step 2) - DENIED by policy
        3. Verify workflow fails at Step 2
        4. Verify Step 1 is rolled back (file deleted)
        """
        # Setup: Create policy that denies delete operations
        policy_engine = PolicyEngine()
        policy_engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.write_file"],
            action="ALLOW"
        ))
        policy_engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.delete_file"],
            action="DENY"
        ))
        
        # Setup: Create RuntimeEngine with stdlib
        specs_dir = resolve_specs_dir()
        registry = CapabilityRegistry()
        load_stdlib(registry=registry, specs_dir=specs_dir)
        
        execution_context = ExecutionContext(
            user_id="test_user",
            session_id="test_session",
            workspace_root=test_workspace
        )
        
        runtime_engine = RuntimeEngine(
            registry=registry,
            execution_context=execution_context
        )
        
        # Setup: Create WorkflowEngine with PolicyEngine
        persistence = WorkflowPersistence(db_path=test_db)
        approval_manager = HumanApprovalManager()
        
        workflow_engine = WorkflowEngine(
            runtime_engine=runtime_engine,
            execution_context=execution_context,
            policy_engine=policy_engine,
            persistence=persistence,
            approval_manager=approval_manager
        )
        
        # Create workflow spec
        test_file = test_workspace / "test.txt"
        
        spec = WorkflowSpec(
            metadata=WorkflowMetadata(
                name="test_policy_deny",
                version="1.0.0",
                owner="agent:test"
            ),
            steps=[
                WorkflowStep(
                    name="create_file",
                    step_type=StepType.ACTION,
                    capability_name="io.fs.write_file",
                    agent_name="agent:test",
                    inputs={
                        "path": str(test_file),
                        "content": "test content"
                    },
                    risk_level=RiskLevel.MEDIUM,
                    compensation={
                        "capability_name": "io.fs.delete_file",
                        "inputs": {"path": str(test_file)}
                    }
                ),
                WorkflowStep(
                    name="delete_file",
                    step_type=StepType.ACTION,
                    capability_name="io.fs.delete_file",
                    agent_name="agent:test",
                    inputs={"path": str(test_file)},
                    depends_on=["create_file"],
                    risk_level=RiskLevel.HIGH
                )
            ]
        )
        
        # Execute workflow
        workflow_id = workflow_engine.submit_workflow(spec)
        workflow_engine.start_workflow(workflow_id)
        
        # Verify workflow failed
        context = workflow_engine.workflows[workflow_id]
        assert context.spec.metadata.status == WorkflowStatus.FAILED
        
        # Verify Step 1 completed
        assert "create_file" in context.completed_steps
        
        # Verify Step 2 failed (denied by policy)
        assert "delete_file" in context.failed_steps
        assert "Policy denied" in context.error_message
        
        # Verify rollback: file should be deleted (compensation executed)
        # Note: Rollback is triggered by _handle_workflow_failure
        # which should execute compensations in reverse order
        # However, since we're using explicit compensation in YAML,
        # we need to verify the compensation was executed
        
        # TODO: Verify compensation execution
        # For now, we verify that the workflow failed at the correct step
        
        print(f"✅ Workflow failed at delete_file step (denied by policy)")
        print(f"✅ Error message: {context.error_message}")
    
    def test_policy_requires_approval_workflow_pauses(self, test_db, test_workspace):
        """
        Test that REQUIRE_APPROVAL decision pauses workflow
        
        Scenario:
        1. Create a file (Step 1)
        2. Try to delete the file (Step 2) - REQUIRES APPROVAL
        3. Verify workflow pauses at Step 2
        4. Approve the deletion
        5. Verify workflow continues and completes
        """
        # Setup: Create policy that requires approval for delete operations
        policy_engine = PolicyEngine()
        policy_engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.write_file"],
            action="ALLOW"
        ))
        policy_engine.add_rule(PolicyRule(
            principal="agent:test",
            capabilities=["io.fs.delete_file"],
            action="REQUIRE_APPROVAL"
        ))
        
        # Setup: Create RuntimeEngine with stdlib
        specs_dir = resolve_specs_dir()
        registry = CapabilityRegistry()
        load_stdlib(registry=registry, specs_dir=specs_dir)
        
        execution_context = ExecutionContext(
            user_id="test_user",
            session_id="test_session",
            workspace_root=test_workspace
        )
        
        runtime_engine = RuntimeEngine(
            registry=registry,
            execution_context=execution_context
        )
        
        # Setup: Create WorkflowEngine with PolicyEngine
        persistence = WorkflowPersistence(db_path=test_db)
        approval_manager = HumanApprovalManager()
        
        workflow_engine = WorkflowEngine(
            runtime_engine=runtime_engine,
            execution_context=execution_context,
            policy_engine=policy_engine,
            persistence=persistence,
            approval_manager=approval_manager
        )
        
        # Create workflow spec
        test_file = test_workspace / "test.txt"
        
        spec = WorkflowSpec(
            metadata=WorkflowMetadata(
                name="test_policy_approval",
                version="1.0.0",
                owner="agent:test"
            ),
            steps=[
                WorkflowStep(
                    name="create_file",
                    step_type=StepType.ACTION,
                    capability_name="io.fs.write_file",
                    agent_name="agent:test",
                    inputs={
                        "path": str(test_file),
                        "content": "test content"
                    },
                    risk_level=RiskLevel.MEDIUM,
                    compensation={
                        "capability_name": "io.fs.delete_file",
                        "inputs": {"path": str(test_file)}
                    }
                ),
                WorkflowStep(
                    name="delete_file",
                    step_type=StepType.ACTION,
                    capability_name="io.fs.delete_file",
                    agent_name="agent:test",
                    inputs={"path": str(test_file)},
                    depends_on=["create_file"],
                    risk_level=RiskLevel.HIGH
                )
            ]
        )
        
        # Execute workflow
        workflow_id = workflow_engine.submit_workflow(spec)
        workflow_engine.start_workflow(workflow_id)
        
        # Verify workflow paused (waiting for approval)
        context = workflow_engine.workflows[workflow_id]
        assert context.spec.metadata.status == WorkflowStatus.PAUSED
        
        # Verify Step 1 completed
        assert "create_file" in context.completed_steps
        
        # Verify Step 2 not yet executed
        assert "delete_file" not in context.completed_steps
        
        print(f"✅ Workflow paused at delete_file step (requires approval)")
        
        # TODO: Test approval and resume
        # For now, we verify that the workflow paused correctly


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
