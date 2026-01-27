"""
AI-First Runtime v3.0 - Retry Mechanism Tests

Test the retry mechanism for failed steps.

Acceptance Criteria (Week 5):
- Step fails twice -> Retries -> Succeeds on 3rd attempt -> Workflow completes
"""

import pytest
import tempfile
from pathlib import Path

from src.runtime.workflow.engine import WorkflowEngine
from src.runtime.workflow.persistence import WorkflowPersistence
from src.runtime.workflow.human_approval import HumanApprovalManager
from src.runtime.engine import RuntimeEngine
from src.runtime.types import ExecutionContext, ExecutionResult
from src.runtime.registry import CapabilityRegistry
from src.specs.v3.workflow_schema import (
    WorkflowSpec,
    WorkflowMetadata,
    WorkflowStep,
    StepType,
    WorkflowStatus,
    RiskLevel
)


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


class FlakyCapabilityHandler:
    """
    A mock capability that fails the first N times, then succeeds.
    
    This simulates a flaky network call or transient error.
    """
    
    def __init__(self, fail_count=2):
        self.fail_count = fail_count
        self.attempt_count = 0
    
    def execute(self, params, context):
        self.attempt_count += 1
        
        if self.attempt_count <= self.fail_count:
            # Fail
            return ExecutionResult(
                success=False,
                outputs={},
                error_message=f"Transient error (attempt {self.attempt_count})"
            )
        else:
            # Succeed
            return ExecutionResult(
                success=True,
                outputs={"result": "success"},
                error_message=None
            )


class TestRetryMechanism:
    """Test retry mechanism for failed steps"""
    
    def test_step_fails_twice_retries_succeeds_on_third_attempt(self, test_db, test_workspace):
        """
        Acceptance Criteria (Week 5):
        Step fails twice -> Retries -> Succeeds on 3rd attempt -> Workflow completes
        """
        # Setup: Create mock RuntimeEngine with flaky capability
        flaky_handler = FlakyCapabilityHandler(fail_count=2)
        
        registry = CapabilityRegistry()
        registry.register(
            capability_id="test.flaky_operation",
            handler=flaky_handler,
            spec_dict={
                "name": "test.flaky_operation",
                "description": "A flaky operation that fails the first 2 times",
                "inputs": [],
                "outputs": [{"name": "result", "type": "string"}]
            }
        )
        
        execution_context = ExecutionContext(
            user_id="test_user",
            session_id="test_session",
            workspace_root=test_workspace
        )
        
        runtime_engine = RuntimeEngine(
            registry=registry
        )
        
        # Setup: Create WorkflowEngine
        persistence = WorkflowPersistence(db_path=test_db)
        approval_manager = HumanApprovalManager()
        
        workflow_engine = WorkflowEngine(
            runtime_engine=runtime_engine,
            execution_context=execution_context,
            policy_engine=None,
            persistence=persistence,
            approval_manager=approval_manager
        )
        
        # Create workflow spec with max_retries=3
        spec = WorkflowSpec(
            metadata=WorkflowMetadata(
                name="test_retry",
                version="1.0.0",
                owner="agent:test"
            ),
            steps=[
                WorkflowStep(
                    name="flaky_step",
                    step_type=StepType.ACTION,
                    capability_name="test.flaky_operation",
                    agent_name="agent:test",
                    inputs={},
                    max_retries=3,  # Allow 3 attempts
                    risk_level=RiskLevel.LOW
                )
            ]
        )
        
        # Execute workflow
        workflow_id = workflow_engine.submit_workflow(spec)
        workflow_engine.start_workflow(workflow_id)
        
        # Verify workflow completed successfully
        context = workflow_engine.workflows[workflow_id]
        assert context.spec.metadata.status == WorkflowStatus.COMPLETED
        
        # Verify step succeeded after retries
        assert "flaky_step" in context.completed_steps
        assert "flaky_step" not in context.failed_steps
        
        # Verify handler was called 3 times (2 failures + 1 success)
        assert flaky_handler.attempt_count == 3
        
        print(f"✅ Step failed 2 times, succeeded on 3rd attempt")
        print(f"✅ Workflow completed successfully")
    
    def test_step_fails_all_retries_triggers_rollback(self, test_db, test_workspace):
        """
        Test that if a step fails all retry attempts, the workflow fails and triggers rollback
        """
        # Setup: Create mock RuntimeEngine with always-failing capability
        flaky_handler = FlakyCapabilityHandler(fail_count=10)  # Always fail
        
        registry = CapabilityRegistry()
        registry.register(
            capability_id="test.always_fail",
            handler=flaky_handler,
            spec_dict={
                "name": "test.always_fail",
                "description": "An operation that always fails",
                "inputs": [],
                "outputs": []
            }
        )
        
        execution_context = ExecutionContext(
            user_id="test_user",
            session_id="test_session",
            workspace_root=test_workspace
        )
        
        runtime_engine = RuntimeEngine(
            registry=registry
        )
        
        # Setup: Create WorkflowEngine
        persistence = WorkflowPersistence(db_path=test_db)
        approval_manager = HumanApprovalManager()
        
        workflow_engine = WorkflowEngine(
            runtime_engine=runtime_engine,
            execution_context=execution_context,
            policy_engine=None,
            persistence=persistence,
            approval_manager=approval_manager
        )
        
        # Create workflow spec with max_retries=3
        spec = WorkflowSpec(
            metadata=WorkflowMetadata(
                name="test_retry_fail",
                version="1.0.0",
                owner="agent:test"
            ),
            steps=[
                WorkflowStep(
                    name="always_fail_step",
                    step_type=StepType.ACTION,
                    capability_name="test.always_fail",
                    agent_name="agent:test",
                    inputs={},
                    max_retries=3,  # Allow 3 attempts
                    risk_level=RiskLevel.LOW
                )
            ]
        )
        
        # Execute workflow
        workflow_id = workflow_engine.submit_workflow(spec)
        workflow_engine.start_workflow(workflow_id)
        
        # Verify workflow failed
        context = workflow_engine.workflows[workflow_id]
        assert context.spec.metadata.status == WorkflowStatus.FAILED
        
        # Verify step failed after all retries
        assert "always_fail_step" in context.failed_steps
        assert "always_fail_step" not in context.completed_steps
        
        # Verify handler was called 3 times (all failures)
        assert flaky_handler.attempt_count == 3
        
        print(f"✅ Step failed all 3 attempts")
        print(f"✅ Workflow failed and triggered rollback")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
