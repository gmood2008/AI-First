"""
AI-First Runtime v3.0 - Transactional Workflow Test

This test demonstrates the core transactional guarantee of AI-First:
If a workflow fails, all completed steps are automatically rolled back.

Test Scenario:
1. Create File A
2. Create File B
3. Fail (simulated error)
4. Verify: Both files are automatically deleted (rolled back)

This is the "Atomic Transaction Demo" requested in the v3.0 launch directive.
"""

import pytest
import os
import tempfile
from pathlib import Path
from datetime import datetime

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from specs.v3.workflow_schema import (
    WorkflowSpec,
    WorkflowStep,
    WorkflowMetadata,
    CompensationStep,
    PolicyRule,
    StepType,
    RiskLevel,
    WorkflowStatus
)
from runtime.workflow.engine import WorkflowEngine, StepExecutionResult


# ============================================================================
# Mock RuntimeEngine for Testing
# ============================================================================

class MockRuntimeEngine:
    """
    A mock RuntimeEngine that simulates file operations.
    
    This allows us to test the workflow engine without a full runtime.
    """
    
    def __init__(self, temp_dir: str):
        self.temp_dir = temp_dir
        self.execution_log = []
    
    def execute(self, capability_id: str, params: dict, context):
        """Execute a capability (mocked)"""
        from runtime.types import ExecutionResult
        
        self.execution_log.append({
            "capability": capability_id,
            "params": params,
            "timestamp": datetime.utcnow()
        })
        
        # For backward compatibility
        capability_name = capability_id
        inputs = params
        
        try:
            if capability_name == "io.fs.create_file":
                result = self._create_file(inputs)
            elif capability_name == "io.fs.delete_file":
                result = self._delete_file(inputs)
            elif capability_name == "test.fail":
                raise RuntimeError("Simulated failure")
            else:
                result = {"status": "success"}
            
            from runtime.types import ExecutionStatus
            return ExecutionResult(
                capability_id=capability_id,
                status=ExecutionStatus.SUCCESS,
                outputs=result
            )
        except Exception as e:
            from runtime.types import ExecutionStatus
            return ExecutionResult(
                capability_id=capability_id,
                status=ExecutionStatus.FAILED,
                outputs={},
                error_message=str(e)
            )
    
    def _create_file(self, inputs: dict) -> dict:
        """Create a file"""
        filename = inputs["filename"]
        content = inputs.get("content", "")
        filepath = os.path.join(self.temp_dir, filename)
        
        with open(filepath, "w") as f:
            f.write(content)
        
        return {"filepath": filepath, "status": "created"}
    
    def _delete_file(self, inputs: dict) -> dict:
        """Delete a file"""
        filepath = inputs["filepath"]
        
        if os.path.exists(filepath):
            os.remove(filepath)
            return {"filepath": filepath, "status": "deleted"}
        else:
            return {"filepath": filepath, "status": "not_found"}


# ============================================================================
# Test Cases
# ============================================================================

class TestTransactionalWorkflow:
    """Test suite for transactional workflow guarantees"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def mock_runtime(self, temp_dir):
        """Create a mock runtime engine"""
        return MockRuntimeEngine(temp_dir)
    
    @pytest.fixture
    def workflow_engine(self, mock_runtime):
        """Create a workflow engine with mock runtime"""
        return WorkflowEngine(runtime_engine=mock_runtime)
    
    def test_atomic_transaction_rollback(self, workflow_engine, mock_runtime, temp_dir):
        """
        Test the core transactional guarantee: automatic rollback on failure.
        
        This is the "Atomic Transaction Demo" from the v3.0 directive.
        """
        # Define the workflow
        spec = WorkflowSpec(
            name="atomic_transaction_demo",
            version="1.0.0",
            description="Demonstrates automatic rollback on failure",
            metadata=WorkflowMetadata(
                owner="test@example.com",
                environment="test"
            ),
            steps=[
                # Step 1: Create File A
                WorkflowStep(
                    name="create_file_a",
                    agent_name="file_agent",
                    capability_name="io.fs.create_file",
                    inputs={
                        "filename": "file_a.txt",
                        "content": "This is File A"
                    },
                    compensation=CompensationStep(
                        step_name="create_file_a",
                        capability_name="io.fs.delete_file",
                        inputs={"filepath": "{{filepath}}"}
                    )
                ),
                # Step 2: Create File B
                WorkflowStep(
                    name="create_file_b",
                    agent_name="file_agent",
                    capability_name="io.fs.create_file",
                    inputs={
                        "filename": "file_b.txt",
                        "content": "This is File B"
                    },
                    depends_on=["create_file_a"],
                    compensation=CompensationStep(
                        step_name="create_file_b",
                        capability_name="io.fs.delete_file",
                        inputs={"filepath": "{{filepath}}"}
                    )
                ),
                # Step 3: Fail (simulated error)
                WorkflowStep(
                    name="fail_step",
                    agent_name="test_agent",
                    capability_name="test.fail",
                    inputs={},
                    depends_on=["create_file_b"]
                )
            ],
            policy=[
                PolicyRule(
                    agent_name="file_agent",
                    allowed_capabilities=["io.fs.create_file", "io.fs.delete_file"]
                )
            ],
            enable_auto_rollback=True
        )
        
        # Submit and start the workflow
        workflow_id = workflow_engine.submit_workflow(spec)
        
        # Verify initial status
        assert workflow_engine.get_workflow_status(workflow_id) == WorkflowStatus.PENDING
        
        # Start execution (this will fail at step 3)
        workflow_engine.start_workflow(workflow_id)
        
        # Verify final status
        assert workflow_engine.get_workflow_status(workflow_id) == WorkflowStatus.ROLLED_BACK
        
        # Verify files were created then deleted (rolled back)
        file_a_path = os.path.join(temp_dir, "file_a.txt")
        file_b_path = os.path.join(temp_dir, "file_b.txt")
        
        assert not os.path.exists(file_a_path), "File A should be deleted after rollback"
        assert not os.path.exists(file_b_path), "File B should be deleted after rollback"
        
        # Verify execution log
        assert len(mock_runtime.execution_log) >= 5  # 2 creates + 1 fail + 2 deletes
        
        print("✅ Atomic Transaction Demo: PASSED")
        print("   - File A created")
        print("   - File B created")
        print("   - Workflow failed at step 3")
        print("   - File B automatically deleted (rolled back)")
        print("   - File A automatically deleted (rolled back)")
        print("   - Final status: ROLLED_BACK")
    
    def test_successful_workflow_no_rollback(self, workflow_engine, mock_runtime, temp_dir):
        """Test that successful workflows do NOT trigger rollback"""
        spec = WorkflowSpec(
            name="successful_workflow",
            version="1.0.0",
            description="A workflow that completes successfully",
            metadata=WorkflowMetadata(
                owner="test@example.com",
                environment="test"
            ),
            steps=[
                WorkflowStep(
                    name="create_file",
                    agent_name="file_agent",
                    capability_name="io.fs.create_file",
                    inputs={
                        "filename": "success.txt",
                        "content": "Success!"
                    },
                    compensation=CompensationStep(
                        step_name="create_file",
                        capability_name="io.fs.delete_file",
                        inputs={"filepath": "{{filepath}}"}
                    )
                )
            ],
            policy=[
                PolicyRule(
                    agent_name="file_agent",
                    allowed_capabilities=["io.fs.create_file"]
                )
            ]
        )
        
        workflow_id = workflow_engine.submit_workflow(spec)
        workflow_engine.start_workflow(workflow_id)
        
        # Verify successful completion
        assert workflow_engine.get_workflow_status(workflow_id) == WorkflowStatus.COMPLETED
        
        # Verify file still exists (NOT rolled back)
        file_path = os.path.join(temp_dir, "success.txt")
        assert os.path.exists(file_path), "File should exist after successful workflow"
        
        with open(file_path, "r") as f:
            assert f.read() == "Success!"
        
        print("✅ Successful Workflow: PASSED")
        print("   - File created")
        print("   - Workflow completed successfully")
        print("   - File NOT rolled back (as expected)")
    
    def test_workflow_validation(self, workflow_engine):
        """Test that invalid workflows are rejected"""
        # Workflow with circular dependency
        spec = WorkflowSpec(
            name="invalid_workflow",
            version="1.0.0",
            description="A workflow with invalid dependencies",
            metadata=WorkflowMetadata(
                owner="test@example.com"
            ),
            steps=[
                WorkflowStep(
                    name="step_a",
                    agent_name="agent",
                    capability_name="test.action",
                    inputs={},
                    depends_on=["step_b"]  # Depends on a step that doesn't exist
                )
            ],
            policy=[]
        )
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid workflow spec"):
            workflow_engine.submit_workflow(spec)
        
        print("✅ Workflow Validation: PASSED")
        print("   - Invalid workflow rejected")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
