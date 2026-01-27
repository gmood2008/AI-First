"""
Test human-in-the-loop approval workflow.

Validates:
- Workflow pauses on HUMAN_APPROVAL step
- Webhook is sent (if configured)
- Workflow can be resumed with approve/reject
- Rejection triggers rollback
"""
import pytest
import os
import tempfile
from pathlib import Path

from src.specs.v3.workflow_schema import (
    WorkflowSpec,
    WorkflowMetadata,
    WorkflowStep,
    StepType,
    RiskLevel
)
from src.runtime.workflow.engine import WorkflowEngine, WorkflowStatus
from src.runtime.workflow.human_approval import HumanApprovalManager
from src.runtime.workflow.persistence import WorkflowPersistence
from src.runtime.engine import RuntimeEngine
from src.runtime.types import ExecutionContext
from src.runtime.registry import CapabilityRegistry
from src.runtime.stdlib.loader import load_stdlib
from src.runtime.mcp.specs_resolver import resolve_specs_dir
from pathlib import Path


def test_human_approval_pause_and_resume():
    """
    Test that workflow pauses on HUMAN_APPROVAL and can be resumed.
    
    Workflow:
    1. Create directory (ACTION)
    2. Human approval (HUMAN_APPROVAL)
    3. Write file (ACTION)
    
    Expected:
    - Workflow pauses after step 1
    - Directory exists
    - After approval, step 3 executes
    - File exists
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "approval_test"
        test_file = test_dir / "approved.txt"
        
        # Create workflow with human approval
        spec = WorkflowSpec(
            name="human_approval_test",
            version="1.0.0",
            description="Test human approval workflow",
            metadata=WorkflowMetadata(
                owner="test_user"
            ),
            steps=[
                WorkflowStep(
                    name="create_dir",
                    step_type=StepType.ACTION,
                    agent_name="test_agent",
                    capability_name="io.fs.make_dir",
                    inputs={"path": str(test_dir)},
                    risk_level=RiskLevel.LOW
                ),
                WorkflowStep(
                    name="approval_gate",
                    step_type=StepType.HUMAN_APPROVAL,
                    agent_name="test_agent",
                    capability_name="human.approve",
                    inputs={"message": "Approve file creation?"},
                    risk_level=RiskLevel.HIGH,
                    description="Human approval required before writing file"
                ),
                WorkflowStep(
                    name="write_file",
                    step_type=StepType.ACTION,
                    agent_name="test_agent",
                    capability_name="io.fs.write_file",
                    inputs={
                        "path": str(test_file),
                        "content": "Approved content"
                    },
                    depends_on=["create_dir", "approval_gate"],
                    risk_level=RiskLevel.MEDIUM
                )
            ]
        )
        
        # Initialize engine
        registry = CapabilityRegistry()
        specs_dir = resolve_specs_dir()
        load_stdlib(registry, specs_dir)
        runtime_engine = RuntimeEngine(registry)
        exec_context = ExecutionContext(
            session_id="test_session",
            user_id="test_user",
            workspace_root=Path(tmpdir),
            confirmation_callback=lambda msg, details: True
        )
        approval_manager = HumanApprovalManager()
        persistence = WorkflowPersistence()
        
        engine = WorkflowEngine(
            runtime_engine=runtime_engine,
            execution_context=exec_context,
            approval_manager=approval_manager,
            persistence=persistence
        )
        
        # Execute workflow (should pause at approval_gate)
        workflow_id = engine.submit_workflow(spec)
        engine.start_workflow(workflow_id)
        
        # Verify workflow is PAUSED
        context = engine.workflows[workflow_id]
        assert context.spec.metadata.status == WorkflowStatus.PAUSED
        
        # Verify directory was created (step 1 completed)
        assert test_dir.exists()
        
        # Verify file does NOT exist yet (step 3 not executed)
        assert not test_file.exists()
        
        # Verify approval is pending
        assert approval_manager.is_pending(workflow_id)
        
        # Approve the workflow
        engine.resume_workflow(workflow_id, decision="approve", approver="test_user")
        
        # Verify workflow completed
        assert context.spec.metadata.status == WorkflowStatus.COMPLETED
        
        # Verify file was created (step 3 executed)
        assert test_file.exists()
        assert test_file.read_text() == "Approved content"
        
        # Verify approval is no longer pending
        assert not approval_manager.is_pending(workflow_id)


def test_human_approval_rejection_triggers_rollback():
    """
    Test that rejecting a workflow triggers rollback.
    
    Workflow:
    1. Create directory (ACTION)
    2. Human approval (HUMAN_APPROVAL)
    3. Write file (ACTION)
    
    Expected:
    - Workflow pauses after step 1
    - Directory exists
    - After rejection, rollback occurs
    - Directory is deleted
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "rejection_test"
        test_file = test_dir / "rejected.txt"
        
        # Create workflow with human approval
        spec = WorkflowSpec(
            name="rejection_test",
            version="1.0.0",
            description="Test rejection triggers rollback",
            metadata=WorkflowMetadata(
                owner="test_user"
            ),
            steps=[
                WorkflowStep(
                    name="create_dir",
                    step_type=StepType.ACTION,
                    agent_name="test_agent",
                    capability_name="io.fs.make_dir",
                    inputs={"path": str(test_dir)},
                    risk_level=RiskLevel.LOW
                ),
                WorkflowStep(
                    name="approval_gate",
                    step_type=StepType.HUMAN_APPROVAL,
                    agent_name="test_agent",
                    capability_name="human.approve",
                    inputs={"message": "Approve file creation?"},
                    risk_level=RiskLevel.HIGH
                ),
                WorkflowStep(
                    name="write_file",
                    step_type=StepType.ACTION,
                    agent_name="test_agent",
                    capability_name="io.fs.write_file",
                    inputs={
                        "path": str(test_file),
                        "content": "This should not exist"
                    },
                    depends_on=["create_dir", "approval_gate"],
                    risk_level=RiskLevel.MEDIUM
                )
            ]
        )
        
        # Initialize engine
        registry = CapabilityRegistry()
        specs_dir = resolve_specs_dir()
        load_stdlib(registry, specs_dir)
        runtime_engine = RuntimeEngine(registry)
        exec_context = ExecutionContext(
            session_id="test_session",
            user_id="test_user",
            workspace_root=Path(tmpdir),
            confirmation_callback=lambda msg, details: True
        )
        approval_manager = HumanApprovalManager()
        persistence = WorkflowPersistence()
        
        engine = WorkflowEngine(
            runtime_engine=runtime_engine,
            execution_context=exec_context,
            approval_manager=approval_manager,
            persistence=persistence
        )
        
        # Execute workflow (should pause at approval_gate)
        workflow_id = engine.submit_workflow(spec)
        engine.start_workflow(workflow_id)
        
        # Verify workflow is PAUSED
        context = engine.workflows[workflow_id]
        assert context.spec.metadata.status == WorkflowStatus.PAUSED
        
        # Verify directory was created
        assert test_dir.exists()
        
        # Reject the workflow
        engine.resume_workflow(workflow_id, decision="reject", approver="test_user")
        
        # Verify workflow failed
        assert context.spec.metadata.status == WorkflowStatus.FAILED
        
        # Verify directory was rolled back (deleted)
        assert not test_dir.exists()
        
        # Verify file was never created
        assert not test_file.exists()


def test_approval_manager_webhook_logging(caplog):
    """
    Test that approval manager logs webhook attempts.
    """
    approval_manager = HumanApprovalManager()
    
    # Request approval without webhook URL
    approval_id = approval_manager.request_approval(
        workflow_id="test_workflow",
        step_id="test_step",
        step_name="Test Step",
        step_info={"capability": "test.action"},
        context={}
    )
    
    # Verify approval is pending
    assert approval_manager.is_pending("test_workflow")
    
    # Verify warning was logged
    assert "No webhook URL configured" in caplog.text


def test_approval_manager_decision_recording():
    """
    Test that approval manager correctly records decisions.
    """
    approval_manager = HumanApprovalManager()
    
    # Request approval
    approval_manager.request_approval(
        workflow_id="test_workflow",
        step_id="test_step",
        step_name="Test Step",
        step_info={},
        context={}
    )
    
    # Record approval
    success = approval_manager.record_decision(
        workflow_id="test_workflow",
        decision="approve",
        approver="test_user"
    )
    
    assert success
    assert approval_manager.get_decision("test_workflow") == "approve"
    assert not approval_manager.is_pending("test_workflow")
    
    # Clear approval
    approval_manager.clear_approval("test_workflow")
    assert approval_manager.get_decision("test_workflow") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
