"""
AI-First Runtime v3.0 - Real Workflow Execution Test

This is the "Real World" integration test that verifies:
1. WorkflowEngine correctly calls RuntimeEngine
2. RuntimeEngine's undo closures are captured
3. Workflow rollback triggers Runtime undo
4. Actual filesystem operations are reversed

Test Scenario:
- Step 1: Create directory logs/
- Step 2 (Parallel): Create logs/a.txt AND logs/b.txt
- Step 3: Fail intentionally
- Verify: logs/ directory is GONE from disk (rollback worked)
"""

import pytest
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

import sys
sys.path.insert(0, '/home/ubuntu/ai-first-runtime/src')

from specs.v3.workflow_schema import (
    WorkflowSpec,
    WorkflowMetadata,
    WorkflowStep,
    StepType,
    RiskLevel,
    WorkflowStatus
)
from runtime.workflow.engine import WorkflowEngine
from runtime.workflow.policy_engine import PolicyEngine, PolicyRule, PolicyDecision
from runtime.engine import RuntimeEngine
from runtime.registry import CapabilityRegistry
from runtime.types import ExecutionContext


class TestRealWorkflowExecution:
    """
    Integration tests for v3.0 WorkflowEngine with real RuntimeEngine.
    
    These tests verify the critical bridge between v3.0 (Workflow Logic)
    and v2.0 (Capability Execution).
    """
    
    @pytest.fixture
    def test_dir(self, tmp_path):
        """Create a temporary directory for test files"""
        test_dir = tmp_path / "workflow_test"
        test_dir.mkdir()
        yield test_dir
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir)
    
    @pytest.fixture
    def runtime_engine(self):
        """Create a RuntimeEngine instance with stdlib capabilities"""
        from runtime.stdlib.loader import load_stdlib
        from runtime.mcp.specs_resolver import resolve_specs_dir
        
        registry = CapabilityRegistry()
        specs_dir = resolve_specs_dir()
        load_stdlib(registry, specs_dir)
        return RuntimeEngine(registry=registry)
    
    @pytest.fixture
    def execution_context(self, tmp_path):
        """Create an ExecutionContext for runtime operations"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        # Auto-approve all confirmations for testing
        def auto_approve_callback(message: str, details: Dict[str, Any]) -> bool:
            return True
        
        return ExecutionContext(
            session_id="test_session",
            user_id="test_user",
            workspace_root=workspace,
            confirmation_callback=auto_approve_callback,
            metadata={}
        )
    
    @pytest.fixture
    def policy_engine(self, tmp_path):
        """Create a PolicyEngine with permissive rules for testing"""
        # Create a temporary policies.yaml
        policies_file = tmp_path / "test_policies.yaml"
        policies_file.write_text("""
default: ALLOW

rules:
  - principal: "agent:*"
    capabilities: ["*"]
    action: ALLOW
""")
        return PolicyEngine(policies_path=policies_file)
    
    @pytest.fixture
    def workflow_engine(self, runtime_engine, execution_context, policy_engine):
        """Create a WorkflowEngine with all components"""
        return WorkflowEngine(
            runtime_engine=runtime_engine,
            execution_context=execution_context,
            policy_engine=policy_engine
        )
    
    def test_simple_workflow_with_rollback(self, workflow_engine, test_dir):
        """
        Test the core integration: Workflow rollback triggers Runtime undo.
        
        This is the acceptance test from the Week 2 directive.
        """
        # Use workspace_root from execution_context
        workspace = workflow_engine.execution_context.workspace_root
        logs_dir = workspace / "logs"
        
        # Define workflow
        workflow = WorkflowSpec(
            name="test_file_operations",
            description="Test workflow with filesystem operations",
            metadata=WorkflowMetadata(
                workflow_id="test_001",
                owner="agent:test",
                version="1.0.0",
                status=WorkflowStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            initial_state={},
            steps=[
                # Step 1: Create directory
                WorkflowStep(
                    agent_name="test_agent",
                    name="create_directory",
                    capability_name="io.fs.make_dir",
                    step_type=StepType.ACTION,
                    inputs={"path": str(logs_dir)},
                    depends_on=[],
                    risk_level=RiskLevel.LOW
                ),
                # Step 2a: Create file a.txt (parallel)
                WorkflowStep(
                    agent_name="test_agent",
                    name="create_file_a",
                    capability_name="io.fs.write_file",
                    step_type=StepType.PARALLEL,
                    inputs={
                        "path": str(logs_dir / "a.txt"),
                        "content": "File A content"
                    },
                    depends_on=["create_directory"],
                    risk_level=RiskLevel.LOW
                ),
                # Step 2b: Create file b.txt (parallel)
                WorkflowStep(
                    agent_name="test_agent",
                    name="create_file_b",
                    capability_name="io.fs.write_file",
                    step_type=StepType.PARALLEL,
                    inputs={
                        "path": str(logs_dir / "b.txt"),
                        "content": "File B content"
                    },
                    depends_on=["create_directory"],
                    risk_level=RiskLevel.LOW
                ),
                # Step 3: This will fail (non-existent capability)
                WorkflowStep(
                    agent_name="test_agent",
                    name="fail_step",
                    capability_name="nonexistent.capability",
                    step_type=StepType.ACTION,
                    inputs={},
                    depends_on=["create_file_a", "create_file_b"],
                    risk_level=RiskLevel.LOW
                )
            ]
        )
        
        # Submit and start workflow
        workflow_id = workflow_engine.submit_workflow(workflow)
        
        # Execute workflow (should fail at step 4)
        workflow_engine.start_workflow(workflow_id)
        
        # Check workflow status
        status = workflow_engine.get_workflow_status(workflow_id)
        assert status == WorkflowStatus.ROLLED_BACK, f"Expected ROLLED_BACK, got {status}"
        
        # CRITICAL VERIFICATION: Check that logs/ directory is GONE
        assert not logs_dir.exists(), "Rollback failed: logs/ directory still exists!"
        assert not (logs_dir / "a.txt").exists(), "Rollback failed: logs/a.txt still exists!"
        assert not (logs_dir / "b.txt").exists(), "Rollback failed: logs/b.txt still exists!"
        
        print("✅ PASS: Workflow rollback successfully deleted all files and directory")
    
    def test_successful_workflow_no_rollback(self, workflow_engine, test_dir):
        """
        Test that successful workflows don't trigger rollback.
        """
        workspace = workflow_engine.execution_context.workspace_root
        logs_dir = workspace / "logs_success"
        
        # Define workflow (no failing step)
        workflow = WorkflowSpec(
            name="test_successful_workflow",
            description="Test workflow that completes successfully",
            metadata=WorkflowMetadata(
                workflow_id="test_002",
                owner="agent:test",
                version="1.0.0",
                status=WorkflowStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            initial_state={},
            steps=[
                WorkflowStep(
                    agent_name="test_agent",
                    name="create_directory",
                    capability_name="io.fs.make_dir",
                    step_type=StepType.ACTION,
                    inputs={"path": str(logs_dir)},
                    depends_on=[],
                    risk_level=RiskLevel.LOW
                ),
                WorkflowStep(
                    agent_name="test_agent",
                    name="create_file",
                    capability_name="io.fs.write_file",
                    step_type=StepType.ACTION,
                    inputs={
                        "path": str(logs_dir / "success.txt"),
                        "content": "Success!"
                    },
                    depends_on=["create_directory"],
                    risk_level=RiskLevel.LOW
                )
            ]
        )
        
        # Submit and start workflow
        workflow_id = workflow_engine.submit_workflow(workflow)
        workflow_engine.start_workflow(workflow_id)
        
        # Verify files exist (no rollback)
        assert logs_dir.exists(), "Directory should exist after successful workflow"
        assert (logs_dir / "success.txt").exists(), "File should exist after successful workflow"
        
        # Read file content
        content = (logs_dir / "success.txt").read_text()
        assert content == "Success!", "File content should match"
        
        print("✅ PASS: Successful workflow completed without rollback")
    
    def test_policy_enforcement(self, workflow_engine, test_dir):
        """
        Test that PolicyEngine blocks unauthorized workflows.
        """
        # Create a restrictive policy engine
        restrictive_policies = tmp_path / "restrictive_policies.yaml"
        restrictive_policies.write_text("""
default: DENY

rules:
  - principal: "agent:authorized"
    capabilities: ["io.fs.*"]
    action: ALLOW
""")
        
        restrictive_policy_engine = PolicyEngine(policies_path=restrictive_policies)
        
        # Create workflow engine with restrictive policies
        restricted_engine = WorkflowEngine(
            runtime_engine=workflow_engine.runtime_engine,
            execution_context=workflow_engine.execution_context,
            policy_engine=restrictive_policy_engine
        )
        
        # Define workflow with unauthorized owner
        workflow = WorkflowSpec(
            name="test_unauthorized_workflow",
            description="Test workflow that should be blocked",
            metadata=WorkflowMetadata(
                workflow_id="test_003",
                owner="agent:unauthorized",  # Not in policy
                version="1.0.0",
                status=WorkflowStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            initial_state={},
            steps=[
                WorkflowStep(
                    agent_name="test_agent",
                    name="create_file",
                    capability_name="io.fs.write_file",
                    step_type=StepType.ACTION,
                    inputs={
                        "path": str(test_dir / "unauthorized.txt"),
                        "content": "Should not be created"
                    },
                    depends_on=[],
                    risk_level=RiskLevel.LOW
                )
            ]
        )
        
        # Submit and start workflow
        workflow_id = restricted_engine.submit_workflow(workflow)
        
        # Should fail due to policy denial
        with pytest.raises(Exception):
            restricted_engine.start_workflow(workflow_id)
        
        # Verify file was NOT created
        assert not (test_dir / "unauthorized.txt").exists(), "Policy enforcement failed: file was created"
        
        print("✅ PASS: PolicyEngine successfully blocked unauthorized workflow")
    
    def test_parallel_execution_with_partial_failure(self, workflow_engine, test_dir):
        """
        Test that parallel execution rolls back all completed steps if one fails.
        """
        workspace = workflow_engine.execution_context.workspace_root
        logs_dir = workspace / "logs_parallel"
        
        # Create directory first (so parallel steps can write to it)
        logs_dir.mkdir()
        
        # Define workflow with parallel steps where one will fail
        workflow = WorkflowSpec(
            name="test_parallel_failure",
            description="Test parallel execution with one failing step",
            metadata=WorkflowMetadata(
                workflow_id="test_004",
                owner="agent:test",
                version="1.0.0",
                status=WorkflowStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            initial_state={},
            steps=[
                # Parallel step 1: Create file a.txt (will succeed)
                WorkflowStep(
                    agent_name="test_agent",
                    name="create_file_a",
                    capability_name="io.fs.write_file",
                    step_type=StepType.PARALLEL,
                    inputs={
                        "path": str(logs_dir / "a.txt"),
                        "content": "File A"
                    },
                    depends_on=[],
                    risk_level=RiskLevel.LOW
                ),
                # Parallel step 2: Create file b.txt (will succeed)
                WorkflowStep(
                    agent_name="test_agent",
                    name="create_file_b",
                    capability_name="io.fs.write_file",
                    step_type=StepType.PARALLEL,
                    inputs={
                        "path": str(logs_dir / "b.txt"),
                        "content": "File B"
                    },
                    depends_on=[],
                    risk_level=RiskLevel.LOW
                ),
                # Parallel step 3: This will fail (invalid path)
                WorkflowStep(
                    agent_name="test_agent",
                    name="create_file_fail",
                    capability_name="io.fs.write_file",
                    step_type=StepType.PARALLEL,
                    inputs={
                        "path": "/invalid/path/c.txt",  # Invalid path
                        "content": "File C"
                    },
                    depends_on=[],
                    risk_level=RiskLevel.LOW
                )
            ]
        )
        
        # Submit and start workflow
        workflow_id = workflow_engine.submit_workflow(workflow)
        
        # Should fail due to invalid path
        with pytest.raises(Exception):
            workflow_engine.start_workflow(workflow_id)
        
        # Verify that a.txt and b.txt were rolled back
        assert not (logs_dir / "a.txt").exists(), "Parallel rollback failed: a.txt still exists"
        assert not (logs_dir / "b.txt").exists(), "Parallel rollback failed: b.txt still exists"
        
        print("✅ PASS: Parallel execution rollback successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
