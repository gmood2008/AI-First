"""
AI-First Runtime v3.0 - Workflow Engine

The Workflow Engine is the core orchestration component that manages the lifecycle
of transactional multi-agent workflows.

Key Responsibilities:
1. Parse and validate WorkflowSpec
2. Manage workflow state transitions (Pending → Running → Completed/Rolled_Back)
3. Execute steps in dependency order
4. Coordinate with the RuntimeEngine for individual step execution
5. Trigger automatic rollback on failure
6. Maintain audit trail

Design Philosophy:
- The engine is a state machine, not an imperative executor
- All state transitions are logged for audit
- Rollback is automatic and atomic
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging
import asyncio
from enum import Enum
import re

from specs.v3.workflow_schema import (
    WorkflowSpec,
    WorkflowStatus,
    WorkflowStep,
    StepType,
    validate_workflow_spec
)
from .persistence import WorkflowPersistence, CompensationIntent
from .recovery import WorkflowRecovery
from .human_approval import HumanApprovalManager
import uuid
import yaml

# Pack Registry integration (optional)
try:
    from registry.pack_registry import PackRegistry, PackState
    PACK_REGISTRY_AVAILABLE = True
except ImportError:
    PACK_REGISTRY_AVAILABLE = False
    PackRegistry = None
    PackState = None


logger = logging.getLogger(__name__)


class StepExecutionResult(Enum):
    """Result of a single step execution"""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PAUSED = "PAUSED"  # For human approval
    SKIPPED = "SKIPPED"


class GovernanceDecision(Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    PAUSE = "PAUSE"


class WorkflowExecutionContext:
    """
    Maintains the runtime state of a workflow execution.

    This is the "working memory" of the workflow engine.
    """

    def __init__(self, spec: WorkflowSpec):
        self.spec = spec
        self.state: Dict[str, Any] = spec.initial_state.copy()
        self.completed_steps: List[str] = []
        self.failed_steps: List[str] = []
        self.compensation_stack: List[tuple] = []  # (step_name, undo_closure)
        self.current_step: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None

    def mark_step_completed(self, step_name: str, result: Dict[str, Any]):
        """Mark a step as completed and update state"""
        self.completed_steps.append(step_name)
        self.state[step_name] = result
        self.state.update(result)
        logger.info(f"Step '{step_name}' completed. State updated.")

    def mark_step_failed(self, step_name: str, error: str):
        """Mark a step as failed"""
        self.failed_steps.append(step_name)
        self.error_message = error
        logger.error(f"Step '{step_name}' failed: {error}")

    def push_compensation(self, step_name: str, undo_closure: Callable):
        """Push a compensation action onto the stack"""
        self.compensation_stack.append((step_name, undo_closure))
        logger.debug(f"Compensation for '{step_name}' pushed to stack")

    def can_execute_step(self, step: WorkflowStep) -> bool:
        """Check if a step's dependencies are satisfied"""
        return all(dep in self.completed_steps for dep in step.depends_on)


class WorkflowEngine:
    """
    The core workflow orchestration engine.

    This is a state machine that transitions workflows through their lifecycle.
    """

    def __init__(
            self,
            runtime_engine=None,
            execution_context=None,
            policy_engine=None,
            constitution_engine=None,
            watchdog=None,
            persistence=None,
            approval_manager=None,
            pack_registry=None,
            governance_hooks: Optional[Dict[str, Callable[..., Any]]] = None):
        """
        Initialize the workflow engine.

        Args:
            runtime_engine: The RuntimeEngine instance for executing individual capabilities
            execution_context: The ExecutionContext for runtime operations (v2.0 compatibility)
            policy_engine: The PolicyEngine for RBAC (optional)
            persistence: The WorkflowPersistence for crash recovery (optional)
            approval_manager: The HumanApprovalManager for human-in-the-loop (optional)
            pack_registry: The PackRegistry for pack-aware execution (optional)
        """
        self.runtime_engine = runtime_engine
        self.execution_context = execution_context
        self.policy_engine = policy_engine
        self.constitution_engine = constitution_engine
        self.watchdog = watchdog
        self.persistence = persistence or WorkflowPersistence()
        self.recovery = WorkflowRecovery(self, self.persistence)
        self.approval_manager = approval_manager or HumanApprovalManager()
        self.pack_registry = pack_registry
        self.governance_hooks = governance_hooks or {}
        self.workflows: Dict[str, WorkflowExecutionContext] = {}

        # Auto-resume running workflows on startup
        self._auto_resume_workflows()

    def submit_workflow(self, spec: WorkflowSpec) -> str:
        """
        Submit a workflow for execution.

        Args:
            spec: The workflow specification

        Returns:
            workflow_id: The unique identifier for this workflow execution

        Raises:
            ValueError: If the workflow specification is invalid
            RuntimeError: If pack is FROZEN or DEPRECATED
        """
        # Validate the spec
        errors = validate_workflow_spec(spec)
        if errors:
            raise ValueError(f"Invalid workflow spec: {errors}")

        # Check pack state if pack_registry is available and workflow has pack context
        if self.pack_registry and PACK_REGISTRY_AVAILABLE and spec.metadata:
            # Prefer pack_id over pack_name (pack_id is the stable identifier)
            pack_id = spec.metadata.pack_id
            pack_name = spec.metadata.pack_name
            pack_version = spec.metadata.pack_version
            
            # Use pack_id if available, otherwise fall back to pack_name
            identifier = pack_id or pack_name
            
            if identifier:
                # Get pack to check state
                pack = self.pack_registry.get_pack(identifier, pack_version)
                if pack:
                    pack_state = self.pack_registry.is_pack_executable(identifier, pack_version)
                    if not pack_state:
                        # Check if it's FROZEN or DEPRECATED
                        key = f"{pack.pack_id}@{pack.version}"
                        if key in self.pack_registry._packs:
                            state = self.pack_registry._packs[key]["state"]
                            if state == PackState.FROZEN:
                                raise RuntimeError(
                                    f"Workflow execution rejected: Pack '{identifier}'@{pack_version or 'latest'} is FROZEN. "
                                    f"This is a governance decision and cannot be overridden."
                                )
                            elif state == PackState.DEPRECATED:
                                raise RuntimeError(
                                    f"Workflow execution rejected: Pack '{identifier}'@{pack_version or 'latest'} is DEPRECATED. "
                                    f"This pack can no longer be used."
                                )
                    
                    if not self.pack_registry.is_pack_executable(identifier, pack_version):
                        raise RuntimeError(
                            f"Workflow execution rejected: Pack '{identifier}'@{pack_version or 'latest'} is not executable."
                        )

        # Create execution context
        context = WorkflowExecutionContext(spec)
        workflow_id = str(uuid.uuid4())
        spec.metadata.workflow_id = workflow_id

        # Register the workflow
        self.workflows[workflow_id] = context

        # Update metadata
        spec.metadata.status = WorkflowStatus.PENDING
        spec.metadata.updated_at = datetime.utcnow()

        # Persist to database
        self.persistence.create_workflow(
            workflow_id=workflow_id,
            name=spec.name,
            owner=spec.metadata.owner,
            spec_yaml=yaml.dump(spec.model_dump(mode='json')),
            context=self.execution_context
        )

        logger.info(
            f"Workflow '{spec.name}' (ID: {workflow_id}) submitted and persisted")
        return workflow_id

    def _auto_resume_workflows(self):
        """Auto-resume workflows on startup (crash recovery)."""
        try:
            resumed_count = self.recovery.auto_resume_workflows()
            if resumed_count > 0:
                logger.info(
                    f"Crash recovery: Resumed {resumed_count} workflows")
        except Exception as e:
            logger.error(f"Crash recovery failed: {e}")

    def start_workflow(self, workflow_id: str):
        """
        Start executing a workflow.

        This transitions the workflow from PENDING to RUNNING and begins step execution.
        
        Raises:
            ValueError: If workflow not found
            RuntimeError: If pack is FROZEN or DEPRECATED
        """
        context = self.workflows.get(workflow_id)
        if not context:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Check pack state before execution
        if self.pack_registry and PACK_REGISTRY_AVAILABLE and context.spec.metadata:
            # Prefer pack_id over pack_name (pack_id is the stable identifier)
            pack_id = context.spec.metadata.pack_id
            pack_name = context.spec.metadata.pack_name
            pack_version = context.spec.metadata.pack_version
            
            # Use pack_id if available, otherwise fall back to pack_name
            identifier = pack_id or pack_name
            
            if identifier:
                # Get pack to check state
                pack = self.pack_registry.get_pack(identifier, pack_version)
                if pack:
                    pack_state = self.pack_registry.is_pack_executable(identifier, pack_version)
                    if not pack_state:
                        # Check if it's FROZEN or DEPRECATED
                        key = f"{pack.pack_id}@{pack.version}"
                        if key in self.pack_registry._packs:
                            state = self.pack_registry._packs[key]["state"]
                            if state == PackState.FROZEN:
                                raise RuntimeError(
                                    f"Workflow execution rejected: Pack '{identifier}'@{pack_version or 'latest'} is FROZEN. "
                                    f"This is a governance decision and cannot be overridden."
                                )
                            elif state == PackState.DEPRECATED:
                                raise RuntimeError(
                                    f"Workflow execution rejected: Pack '{identifier}'@{pack_version or 'latest'} is DEPRECATED. "
                                    f"This pack can no longer be used."
                                )
                    
                    if not self.pack_registry.is_pack_executable(identifier, pack_version):
                        raise RuntimeError(
                            f"Workflow execution rejected: Pack '{identifier}'@{pack_version or 'latest'} is not executable."
                        )

        # Transition to RUNNING
        context.spec.metadata.status = WorkflowStatus.RUNNING
        context.spec.metadata.started_at = datetime.utcnow()
        context.spec.metadata.updated_at = datetime.utcnow()
        context.started_at = datetime.utcnow()

        logger.info(f"Workflow {workflow_id} started")

        hook = self.governance_hooks.get("pre_execution")
        if hook is not None:
            decision = hook(
                trace_id=(getattr(self.execution_context, "metadata", {}) or {}).get("traceId"),
                workflow_id=workflow_id,
                workflow_spec=context.spec,
                context=self.execution_context,
            )
            if decision == GovernanceDecision.DENY or str(decision) == GovernanceDecision.DENY.value:
                msg = "Governance denied workflow execution"
                self._handle_workflow_failure(context, msg)
                raise RuntimeError(msg)
            if decision == GovernanceDecision.PAUSE or str(decision) == GovernanceDecision.PAUSE.value:
                self.persistence.update_workflow_status(
                    workflow_id=workflow_id,
                    status=WorkflowStatus.PAUSED,
                )
                context.spec.metadata.status = WorkflowStatus.PAUSED
                context.spec.metadata.updated_at = datetime.utcnow()
                return

        # Execute steps
        try:
            self._execute_workflow(context)
        except Exception as e:
            logger.error(f"Workflow {workflow_id} failed: {e}")
            self._handle_workflow_failure(context, str(e))

    def _execute_workflow(self, context: WorkflowExecutionContext):
        """
        Execute all steps in the workflow.

        Supports both sequential and parallel execution based on step types.
        """
        spec = context.spec

        # Execution with dependency resolution and parallel support
        # Filter out already completed steps (important for resume)
        remaining_steps = [
            step for step in spec.steps
            if step.name not in context.completed_steps
        ]

        while remaining_steps:
            # Find all steps that can be executed (dependencies satisfied)
            executable_steps = [
                step for step in remaining_steps
                if context.can_execute_step(step)
            ]

            if not executable_steps:
                # Deadlock or circular dependency
                raise RuntimeError(
                    "No executable steps found. Possible circular dependency.")

            # Check if we have parallel steps
            parallel_steps = [
                s for s in executable_steps if s.step_type == StepType.PARALLEL]

            if parallel_steps:
                # Execute parallel steps concurrently
                logger.info(
                    f"Executing {len(parallel_steps)} steps in parallel")
                success = self._execute_parallel_steps(context, parallel_steps)

                if not success:
                    # At least one parallel step failed
                    raise RuntimeError("One or more parallel steps failed")

                # Remove all successful parallel steps
                for step in parallel_steps:
                    remaining_steps.remove(step)
            else:
                # Execute one sequential step
                step = executable_steps[0]
                context.current_step = step.name
                result = self._execute_step(context, step)

                if result == StepExecutionResult.SUCCESS:
                    remaining_steps.remove(step)
                elif result == StepExecutionResult.PAUSED:
                    # Workflow is paused (e.g., waiting for human approval)
                    # Mark step as completed so it won't be re-executed on
                    # resume
                    context.mark_step_completed(step.name, {})
                    remaining_steps.remove(step)
                    spec.metadata.status = WorkflowStatus.PAUSED
                    spec.metadata.updated_at = datetime.utcnow()
                    logger.info(
                        f"Workflow {spec.metadata.workflow_id} paused at step '{step.name}'")
                    return
                else:
                    # Step failed
                    raise RuntimeError(f"Step '{step.name}' failed")

        # All steps completed successfully
        self._complete_workflow(context)

    def _execute_parallel_steps(self,
                                context: WorkflowExecutionContext,
                                steps: List[WorkflowStep]) -> bool:
        """
        Execute multiple steps in parallel using asyncio.

        If any step fails, all completed steps are rolled back.

        Args:
            context: The workflow execution context
            steps: List of steps to execute in parallel

        Returns:
            True if all steps succeeded, False if any failed
        """
        # Track which steps succeeded (for rollback if needed)
        succeeded_steps = []
        failed_step = None

        try:
            # Execute all steps
            for step in steps:
                context.current_step = step.name
                result = self._execute_step(context, step)

                if result == StepExecutionResult.SUCCESS:
                    succeeded_steps.append(step)
                else:
                    failed_step = step
                    break

            # Check if all succeeded
            if failed_step is None:
                logger.info(
                    f"All {len(steps)} parallel steps completed successfully")
                return True

            # At least one step failed - rollback all succeeded steps
            logger.error(
                f"Parallel step '{failed_step.name}' failed. Rolling back {len(succeeded_steps)} completed steps.")

            # Rollback in reverse order (LIFO)
            for step in reversed(succeeded_steps):
                # Find and execute the compensation for this step
                for comp_step_name, undo_closure in reversed(
                        context.compensation_stack):
                    if comp_step_name == step.name:
                        logger.info(
                            f"Rolling back parallel step '{step.name}'")
                        undo_closure()
                        context.compensation_stack.remove(
                            (comp_step_name, undo_closure))
                        break

            return False

        except Exception as e:
            logger.error(f"Exception during parallel execution: {e}")
            # Rollback all succeeded steps
            for step in reversed(succeeded_steps):
                for comp_step_name, undo_closure in reversed(
                        context.compensation_stack):
                    if comp_step_name == step.name:
                        logger.info(
                            f"Rolling back parallel step '{step.name}' due to exception")
                        undo_closure()
                        context.compensation_stack.remove(
                            (comp_step_name, undo_closure))
                        break
            return False

    def _execute_step(self, context: WorkflowExecutionContext,
                      step: WorkflowStep) -> StepExecutionResult:
        """
        Execute a single workflow step.

        Args:
            context: The workflow execution context
            step: The step to execute

        Returns:
            StepExecutionResult indicating the outcome
        """
        logger.info(
            f"Executing step '{step.name}' (capability: {step.capability_name})")

        if self.watchdog:
            try:
                workflow_id = context.spec.metadata.workflow_id
                self.watchdog.enforce_not_expired(
                    workflow_id=workflow_id,
                    metadata={"workflow": context.spec.name, "step": step.name},
                )
            except Exception as e:
                error_msg = f"Watchdog timeout: {e}"
                logger.error(error_msg)
                context.mark_step_failed(step.name, error_msg)
                return StepExecutionResult.FAILURE

        if self.constitution_engine:
            workflow_owner = context.spec.metadata.owner
            side_effects: List[str] = []
            try:
                if self.runtime_engine and hasattr(self.runtime_engine, "registry"):
                    handler = self.runtime_engine.registry.get_handler(step.capability_name)
                    side_effects = handler.contracts.get("side_effects", []) if getattr(handler, "contracts", None) else []
            except Exception:
                side_effects = []

            try:
                self.constitution_engine.enforce(
                    capability_id=step.capability_name,
                    principal=workflow_owner,
                    side_effects=side_effects,
                    context={"workflow": context.spec.name, "step": step.name},
                )
            except Exception as e:
                error_msg = f"Constitution denied: {step.capability_name} ({e})"
                logger.error(error_msg)
                context.mark_step_failed(step.name, error_msg)
                return StepExecutionResult.FAILURE

        # POLICY CHECK: Verify permission before execution
        if self.policy_engine:
            from runtime.workflow.policy_engine import PolicyDecision

            workflow_owner = context.spec.metadata.owner
            decision = self.policy_engine.check_permission(
                principal=workflow_owner,
                capability_id=step.capability_name,
                risk_level=step.risk_level
            )

            if decision == PolicyDecision.DENY:
                error_msg = f"Policy denied: {workflow_owner} lacks permission for {step.capability_name}"
                logger.error(error_msg)
                context.mark_step_failed(step.name, error_msg)
                return StepExecutionResult.FAILURE
            elif decision == PolicyDecision.REQUIRE_APPROVAL:
                logger.info(
                    f"Step '{step.name}' requires human approval (policy escalation)")
                return StepExecutionResult.PAUSED

        # Handle different step types
        if step.step_type == StepType.HUMAN_APPROVAL:
            # Request human approval via webhook
            workflow_id = context.spec.metadata.workflow_id
            self.approval_manager.request_approval(
                workflow_id=workflow_id,
                step_id=step.name,
                step_name=step.name,
                step_info={
                    "capability": step.capability_name,
                    "inputs": step.inputs,
                    "risk_level": step.risk_level.value if step.risk_level else "unknown",
                    "description": step.description or "No description"},
                context={
                    "state": context.state})

            # Update workflow status to PAUSED
            self.persistence.update_workflow_status(
                workflow_id=workflow_id,
                status=WorkflowStatus.PAUSED
            )

            # CHECKPOINT: Save HUMAN_APPROVAL step to database
            self.recovery.checkpoint_step(
                workflow_id=workflow_id,
                step_id=step.name,
                step_name=step.name,
                capability_id=step.capability_name,
                agent_name=step.agent_name,
                status="PAUSED",  # Mark as PAUSED, not COMPLETED
                execution_order=len(context.completed_steps),
                inputs=step.inputs,
                outputs={}
            )

            logger.info(
                f"Step '{step.name}' requires human approval. Workflow paused.")
            return StepExecutionResult.PAUSED

        # For ACTION steps, delegate to RuntimeEngine
        if self.runtime_engine:
            try:
                # Resolve inputs with template variables
                resolved_params = self._resolve_inputs(context, step.inputs)

                hook = self.governance_hooks.get("pre_step")
                if hook is not None:
                    decision = hook(
                        trace_id=(getattr(self.execution_context, "metadata", {}) or {}).get("traceId"),
                        workflow_id=context.spec.metadata.workflow_id,
                        step=step,
                        resolved_inputs=resolved_params,
                        context=self.execution_context,
                    )
                    if decision == GovernanceDecision.DENY or str(decision) == GovernanceDecision.DENY.value:
                        error_msg = f"Governance denied step: {step.name}"
                        context.mark_step_failed(step.name, error_msg)
                        self.recovery.checkpoint_step(
                            workflow_id=context.spec.metadata.workflow_id,
                            step_id=step.name,
                            step_name=step.name,
                            capability_id=step.capability_name,
                            agent_name=step.agent_name,
                            status="FAILED",
                            execution_order=len(context.completed_steps),
                            inputs=resolved_params,
                            outputs={},
                            error_message=error_msg,
                        )
                        return StepExecutionResult.FAILURE
                    if decision == GovernanceDecision.PAUSE or str(decision) == GovernanceDecision.PAUSE.value:
                        workflow_id = context.spec.metadata.workflow_id
                        self.persistence.update_workflow_status(
                            workflow_id=workflow_id,
                            status=WorkflowStatus.PAUSED,
                        )
                        self.recovery.checkpoint_step(
                            workflow_id=workflow_id,
                            step_id=step.name,
                            step_name=step.name,
                            capability_id=step.capability_name,
                            agent_name=step.agent_name,
                            status="PAUSED",
                            execution_order=len(context.completed_steps),
                            inputs=resolved_params,
                            outputs={},
                        )
                        return StepExecutionResult.PAUSED

                # RETRY LOGIC: Attempt execution with retries
                max_retries = step.max_retries or 3
                last_error = None
                
                for attempt in range(max_retries):
                    # Execute the capability via RuntimeEngine (v2.0 bridge)
                    execution_result = self.runtime_engine.execute(
                        capability_id=step.capability_name,
                        params=resolved_params,
                        context=self.execution_context
                    )

                    # Check if execution was successful
                    if execution_result.is_success():
                        # Success! Break out of retry loop
                        break
                    else:
                        # Failure: Log and retry
                        last_error = execution_result.error_message or "Unknown error"
                        logger.warning(
                            f"Step '{step.name}' failed (attempt {attempt + 1}/{max_retries}): {last_error}")
                        
                        # If this was the last attempt, mark as failed
                        if attempt == max_retries - 1:
                            logger.error(
                                f"Step '{step.name}' failed after {max_retries} attempts")
                            context.mark_step_failed(step.name, last_error)
                            return StepExecutionResult.FAILURE
                        
                        # Otherwise, continue to next retry
                        logger.info(f"Retrying step '{step.name}'...")
                        continue

                # Mark step as completed with outputs
                context.mark_step_completed(
                    step.name, execution_result.outputs)

                # CHECKPOINT: Save step completion to database
                workflow_id = context.spec.metadata.workflow_id
                self.recovery.checkpoint_step(
                    workflow_id=workflow_id,
                    step_id=step.name,
                    step_name=step.name,
                    capability_id=step.capability_name,
                    agent_name=step.agent_name,
                    status="COMPLETED",
                    execution_order=len(context.completed_steps),
                    inputs=resolved_params,
                    outputs=execution_result.outputs
                )

                hook = self.governance_hooks.get("post_step")
                if hook is not None:
                    hook(
                        trace_id=(getattr(self.execution_context, "metadata", {}) or {}).get("traceId"),
                        workflow_id=context.spec.metadata.workflow_id,
                        step=step,
                        resolved_inputs=resolved_params,
                        result=execution_result,
                        context=self.execution_context,
                    )

                # CRITICAL: Extract undo closure from RuntimeEngine's UndoRecord
                # This unifies v2.0 "Atomic Undo" with v3.0 "Workflow Rollback"
                if execution_result.undo_record:
                    undo_closure = execution_result.undo_record.undo_function
                    context.push_compensation(step.name, undo_closure)

                    # CHECKPOINT: Save compensation intent to database
                    # For now, we create a basic intent from the undo record
                    intent = self._create_compensation_intent(
                        step, resolved_params, execution_result.outputs)
                    self.recovery.checkpoint_compensation(
                        workflow_id=workflow_id,
                        step_id=step.name,
                        intent=intent
                    )

                    logger.debug(
                        f"Captured and checkpointed undo closure for step '{step.name}'")
                elif step.compensation:
                    # Fallback: Use workflow-defined compensation if no runtime
                    # undo available
                    undo_closure = self._create_compensation_closure(
                        context, step)
                    context.push_compensation(step.name, undo_closure)
                    logger.debug(
                        f"Using workflow-defined compensation for step '{step.name}'")

                return StepExecutionResult.SUCCESS

            except Exception as e:
                context.mark_step_failed(step.name, str(e))

                hook = self.governance_hooks.get("post_step")
                if hook is not None:
                    hook(
                        trace_id=(getattr(self.execution_context, "metadata", {}) or {}).get("traceId"),
                        workflow_id=context.spec.metadata.workflow_id,
                        step=step,
                        resolved_inputs=None,
                        result={"status": "FAILURE", "error": str(e)},
                        context=self.execution_context,
                    )
                return StepExecutionResult.FAILURE
        else:
            # No runtime engine (for testing)
            logger.warning(
                "No RuntimeEngine configured. Step execution simulated.")
            context.mark_step_completed(step.name, {"status": "simulated"})
            return StepExecutionResult.SUCCESS

    def _resolve_inputs(
        self,
        context: WorkflowExecutionContext,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Resolve template variables in step inputs."""

        pattern = re.compile(r"\{\{\s*([a-zA-Z0-9_\-\.]+)\s*\}\}")
        full_pattern = re.compile(r"^\{\{\s*([a-zA-Z0-9_\-\.]+)\s*\}\}$")

        def _resolve_value(value: Any) -> Any:
            if isinstance(value, dict):
                return {k: _resolve_value(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_resolve_value(v) for v in value]
            if isinstance(value, str):
                def _get_state_value(path: str) -> Any:
                    cur: Any = context.state
                    for part in path.split("."):
                        if not isinstance(cur, dict):
                            return None
                        if part not in cur:
                            return None
                        cur = cur[part]
                    return cur

                m_full = full_pattern.match(value)
                if m_full:
                    v_full = _get_state_value(m_full.group(1))
                    if v_full is not None:
                        return v_full

                def _sub(m: re.Match) -> str:
                    var_name = m.group(1)
                    v = _get_state_value(var_name)
                    if v is None:
                        return m.group(0)
                    if isinstance(v, (dict, list)):
                        try:
                            import json

                            return json.dumps(v, ensure_ascii=False, indent=2)
                        except Exception:
                            return str(v)
                    return str(v)

                return pattern.sub(_sub, value)
            return value

        return _resolve_value(inputs)

    def _create_compensation_closure(self,
                                     context: WorkflowExecutionContext,
                                     step: WorkflowStep) -> Callable:
        """
        Create a closure that can undo this step.

        This is the core of the transactional model.
        The closure captures the current state snapshot to ensure correct rollback.
        """
        compensation = step.compensation
        # Capture the current state snapshot for rollback
        captured_state = context.state.copy()

        def undo():
            logger.info(
                f"Rolling back step '{step.name}' using '{compensation.capability_name}'")
            if self.runtime_engine:
                # Resolve inputs using the captured state snapshot
                resolved_inputs = {}
                for key, value in compensation.inputs.items():
                    if isinstance(value, str) and value.startswith(
                            "{{") and value.endswith("}}"):
                        var_name = value[2:-2].strip()
                        resolved_inputs[key] = captured_state.get(
                            var_name, value)
                    else:
                        resolved_inputs[key] = value

                self.runtime_engine.execute(
                    capability_id=compensation.capability_name,
                    params=resolved_inputs,
                    context=self.execution_context
                )

        return undo

    def _complete_workflow(self, context: WorkflowExecutionContext):
        """Mark the workflow as successfully completed"""
        context.spec.metadata.status = WorkflowStatus.COMPLETED
        context.spec.metadata.completed_at = datetime.utcnow()
        context.spec.metadata.updated_at = datetime.utcnow()
        context.completed_at = datetime.utcnow()

        try:
            self.persistence.update_workflow_status(
                workflow_id=context.spec.metadata.workflow_id,
                status=WorkflowStatus.COMPLETED,
            )
        except Exception:
            pass

        logger.info(
            f"Workflow {context.spec.metadata.workflow_id} completed successfully")

        hook = self.governance_hooks.get("post_execution")
        if hook is not None:
            hook(
                trace_id=(getattr(self.execution_context, "metadata", {}) or {}).get("traceId"),
                workflow_id=context.spec.metadata.workflow_id,
                summary={"status": "SUCCESS"},
                context=self.execution_context,
            )

    def _handle_workflow_failure(
            self,
            context: WorkflowExecutionContext,
            error: str):
        """
        Handle workflow failure by triggering automatic rollback.

        This is the transactional guarantee: if the workflow fails, all completed
        steps are undone in reverse order.
        """
        spec = context.spec
        logger.error(f"Workflow {spec.metadata.workflow_id} failed: {error}")

        # Mark as failed
        spec.metadata.status = WorkflowStatus.FAILED
        spec.metadata.updated_at = datetime.utcnow()
        context.error_message = error

        try:
            self.persistence.update_workflow_status(
                workflow_id=spec.metadata.workflow_id,
                status=WorkflowStatus.FAILED,
                error_message=error,
            )
        except Exception:
            pass

        # Trigger rollback if enabled
        if spec.enable_auto_rollback:
            self._rollback_workflow(context)

        hook = self.governance_hooks.get("post_execution")
        if hook is not None:
            hook(
                trace_id=(getattr(self.execution_context, "metadata", {}) or {}).get("traceId"),
                workflow_id=context.spec.metadata.workflow_id,
                summary={"status": "FAILED", "error": error},
                context=self.execution_context,
            )

    def _rollback_workflow(self, context: WorkflowExecutionContext):
        """
        Rollback all completed steps in reverse order.

        This implements the compensation-based transaction model.
        """
        logger.info(
            f"Rolling back workflow {context.spec.metadata.workflow_id}")

        # Execute compensations in reverse order (LIFO)
        while context.compensation_stack:
            step_name, undo_closure = context.compensation_stack.pop()
            try:
                logger.info(f"Compensating step '{step_name}'")
                undo_closure()
            except Exception as e:
                logger.error(
                    f"Compensation for step '{step_name}' failed: {e}")
                # Continue with remaining compensations

        # Mark as rolled back
        context.spec.metadata.status = WorkflowStatus.ROLLED_BACK
        context.spec.metadata.updated_at = datetime.utcnow()

        logger.info(
            f"Workflow {context.spec.metadata.workflow_id} rolled back successfully")

    def get_workflow_status(
            self,
            workflow_id: str) -> Optional[WorkflowStatus]:
        """Get the current status of a workflow"""
        context = self.workflows.get(workflow_id)
        return context.spec.metadata.status if context else None

    def _create_compensation_intent(
        self,
        step: WorkflowStep,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> CompensationIntent:
        """
        Create a CompensationIntent from a step execution.

        This converts the runtime undo closure into a serializable intent.

        Args:
            step: The workflow step
            inputs: The resolved inputs
            outputs: The execution outputs

        Returns:
            CompensationIntent for database storage
        """
        # Determine action based on capability
        capability_id = step.capability_name
        action = "unknown"
        params = {}
        metadata = {}

        # File system operations
        if capability_id == "io.fs.make_dir":
            action = "delete"
            params = {"path": inputs.get("path"), "step_name": step.name}
        elif capability_id == "io.fs.write_file":
            action = "delete"
            params = {"path": inputs.get("path"), "step_name": step.name}
            # Store original content if we want to support restore
            # metadata["original_content"] = ...
        elif capability_id == "io.fs.delete":
            action = "restore"
            params = {"path": inputs.get("path"), "step_name": step.name}
            # Would need to store original content

        # Add more capability mappings as needed

        return CompensationIntent(
            action=action,
            capability_id=capability_id,
            params=params,
            metadata=metadata
        )

    def resume_workflow(
            self,
            workflow_id: str,
            decision: str,
            approver: Optional[str] = None):
        """
        Resume a PAUSED workflow after human approval.

        Args:
            workflow_id: Workflow identifier
            decision: "approve" or "reject"
            approver: Who made the decision (optional)
        """
        if workflow_id not in self.workflows:
            try:
                self._auto_resume_workflows()
            except Exception:
                pass

        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")

        context = self.workflows[workflow_id]

        if context.spec.metadata.status != WorkflowStatus.PAUSED:
            raise ValueError(
                f"Workflow {workflow_id} is not paused (current status: {context.spec.metadata.status})")

        # Record decision
        self.approval_manager.record_decision(workflow_id, decision, approver)

        if decision == "approve":
            logger.info(
                f"Workflow {workflow_id} approved by {approver}. Resuming...")
            # Mark paused steps as completed in persistence so bridge output reflects post-approval progress.
            try:
                self.persistence.update_workflow_step_statuses(
                    workflow_id=workflow_id,
                    from_status="paused",
                    to_status="completed",
                )
            except Exception:
                pass
            # Update status to RUNNING
            self.persistence.update_workflow_status(
                workflow_id, WorkflowStatus.RUNNING)
            context.spec.metadata.status = WorkflowStatus.RUNNING
            # Continue execution (the paused step will be skipped or marked as
            # approved)
            self._execute_workflow(context)
        elif decision == "reject":
            logger.info(
                f"Workflow {workflow_id} rejected by {approver}. Rolling back...")
            # Rollback and mark as FAILED
            self._rollback_workflow(context)
            context.error_message = "Rejected by human approver"
            # Override status to FAILED (rollback sets it to ROLLED_BACK)
            context.spec.metadata.status = WorkflowStatus.FAILED
            self.persistence.update_workflow_status(
                workflow_id,
                WorkflowStatus.FAILED,
                error_message="Rejected by human approver"
            )
        else:
            raise ValueError(
                f"Invalid decision: {decision}. Must be 'approve' or 'reject'.")

    def cancel_workflow(
            self,
            workflow_id: str,
            reason: str = "Cancelled",
            rollback: bool = False) -> None:
        if workflow_id not in self.workflows:
            try:
                self._auto_resume_workflows()
            except Exception:
                pass

        if rollback:
            try:
                self.recovery.rollback_workflow(workflow_id, reason=reason)
            except Exception:
                pass

        self.persistence.update_workflow_status(
            workflow_id=workflow_id,
            status=WorkflowStatus.FAILED,
            error_message=reason,
        )

        context = self.workflows.get(workflow_id)
        if context is not None:
            context.error_message = reason
            context.spec.metadata.status = WorkflowStatus.FAILED

    def rollback_workflow(self, workflow_id: str, reason: str = "Manual rollback") -> bool:
        try:
            return self.recovery.rollback_workflow(workflow_id, reason=reason)
        except Exception:
            return False
