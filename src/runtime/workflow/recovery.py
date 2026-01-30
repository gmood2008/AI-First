"""
Crash Recovery Module for AI-First Runtime v3.0

Provides automatic workflow resumption after crashes:
- Auto-resume RUNNING workflows on startup
- Reconstruct compensation stack from database
- Support manual resume/rollback via CLI
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .persistence import WorkflowPersistence, WorkflowStatus as PersistenceWorkflowStatus, CompensationIntent
from specs.v3.workflow_schema import WorkflowSpec, WorkflowStatus
import yaml

logger = logging.getLogger(__name__)


class WorkflowRecovery:
    """
    Handles crash recovery and workflow resumption.

    This module is responsible for:
    1. Detecting crashed workflows on startup
    2. Reconstructing workflow state from database
    3. Resuming or rolling back workflows
    """

    def __init__(self, engine, persistence: WorkflowPersistence):
        """
        Initialize recovery manager.

        Args:
            engine: The WorkflowEngine instance
            persistence: The WorkflowPersistence instance
        """
        self.engine = engine
        self.persistence = persistence

    def auto_resume_workflows(self) -> int:
        """
        Auto-resume all RUNNING or PAUSED workflows on startup.

        Returns:
            Number of workflows resumed
        """
        running_workflows = self.persistence.get_running_workflows()

        if not running_workflows:
            logger.info("No workflows to resume")
            return 0

        logger.info(f"Found {len(running_workflows)} workflows to resume")

        resumed_count = 0
        for workflow_record in running_workflows:
            try:
                workflow_id = workflow_record["id"]
                status = workflow_record["status"]

                logger.info(
                    f"Resuming workflow {workflow_id} (status: {status})")

                # Reconstruct workflow spec from YAML
                spec_dict = yaml.safe_load(workflow_record["spec_yaml"])
                if isinstance(spec_dict, dict):
                    metadata = spec_dict.get("metadata")
                    if isinstance(metadata, dict):
                        raw_status = metadata.get("status")
                        if raw_status is not None:
                            # Persisted workflows store lowercase status values (e.g. 'paused'),
                            # but the v3 WorkflowSpec schema expects uppercase enum values (e.g. 'PAUSED').
                            metadata["status"] = str(raw_status).upper()
                spec = WorkflowSpec(**spec_dict)

                # Align spec metadata with persisted workflow status
                try:
                    if getattr(spec, "metadata", None) is not None:
                        spec.metadata.status = WorkflowStatus(str(status).upper())
                except Exception:
                    # Keep original spec metadata if status cannot be parsed
                    pass

                # Reconstruct execution context
                from .engine import WorkflowExecutionContext
                context = WorkflowExecutionContext(spec)

                # Restore completed steps
                steps = self.persistence.get_workflow_steps(workflow_id)
                for step_record in steps:
                    step_status = step_record.get("status")
                    step_status_text = str(step_status).lower() if step_status is not None else ""
                    if "." in step_status_text:
                        step_status_text = step_status_text.split(".")[-1]

                    # Engine marks a PAUSED step as completed so it won't be re-executed on resume.
                    if step_status_text in {"completed", "paused"}:
                        context.completed_steps.append(step_record["step_id"])
                        if step_record.get("outputs_json"):
                            import json

                            outputs = json.loads(step_record["outputs_json"])
                            context.state.update(outputs)

                # Restore compensation stack
                compensation_intents = self.persistence.get_compensation_stack(
                    workflow_id)
                for intent in reversed(
                        compensation_intents):  # Reverse to get FIFO order
                    # Convert CompensationIntent to executable closure
                    undo_closure = self._intent_to_closure(intent)
                    context.compensation_stack.append(
                        (intent.params.get("step_name", "unknown"), undo_closure))

                # Register in engine
                self.engine.workflows[workflow_id] = context

                # Resume execution if RUNNING
                if status == PersistenceWorkflowStatus.RUNNING.value:
                    logger.info(
                        f"Auto-resuming RUNNING workflow {workflow_id}")
                    # Note: Actual resumption happens in the main event loop
                    # For now, we just mark it as ready
                    resumed_count += 1
                elif status == PersistenceWorkflowStatus.PAUSED.value:
                    logger.info(
                        f"Workflow {workflow_id} is PAUSED (waiting for human approval)")
                    resumed_count += 1

            except Exception as e:
                logger.error(
                    f"Failed to resume workflow {workflow_record['id']}: {e}")
                # Mark workflow as FAILED
                self.persistence.update_workflow_status(
                    workflow_id=workflow_record["id"],
                    status=PersistenceWorkflowStatus.FAILED,
                    error_message=f"Recovery failed: {str(e)}"
                )

        logger.info(f"Successfully resumed {resumed_count} workflows")
        return resumed_count

    def _intent_to_closure(self, intent: CompensationIntent):
        """
        Convert a CompensationIntent to an executable closure.

        This is the reverse of serialization - we reconstruct the undo operation
        from the stored intent.

        Args:
            intent: The compensation intent

        Returns:
            A callable that performs the undo operation
        """
        def undo_closure():
            """Execute the compensation based on intent."""
            try:
                action = intent.action
                capability_id = intent.capability_id
                params = intent.params

                logger.info(
                    f"Executing compensation: {action} via {capability_id}")

                # For Alpha, we support basic file operations
                if action == "delete" and capability_id.startswith("io.fs"):
                    # Delete a file or directory
                    import os
                    path = params.get("path")
                    if path and os.path.exists(path):
                        if os.path.isdir(path):
                            import shutil
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                        logger.info(f"Deleted {path}")

                elif action == "restore" and capability_id.startswith("io.fs"):
                    # Restore a file from metadata
                    path = params.get("path")
                    content = intent.metadata.get("original_content")
                    if path and content:
                        with open(path, 'w') as f:
                            f.write(content)
                        logger.info(f"Restored {path}")

                else:
                    logger.warning(
                        f"Unsupported compensation action: {action} for {capability_id}")

            except Exception as e:
                logger.error(f"Compensation failed: {e}")
                raise

        return undo_closure

    def rollback_workflow(
        self,
        workflow_id: str,
        reason: str = "Manual rollback",
    ) -> bool:
        """
        Run compensation stack for a workflow and mark it ROLLED_BACK.

        Args:
            workflow_id: Workflow identifier
            reason: Reason for rollback (e.g. "Global rollback from dashboard")

        Returns:
            True if rollback was performed, False if workflow not active or no compensations
        """
        running = self.persistence.get_running_workflows()
        if not any(w.get("id") == workflow_id for w in running):
            logger.warning("Workflow %s is not RUNNING/PAUSED; skipping rollback", workflow_id)
            return False

        stack = self.persistence.get_compensation_stack(workflow_id)
        for intent in stack:
            try:
                closure = self._intent_to_closure(intent)
                closure()
            except Exception as e:
                logger.error("Compensation failed for workflow %s: %s", workflow_id, e)
                self.persistence.update_workflow_status(
                    workflow_id=workflow_id,
                    status=WorkflowStatus.ROLLED_BACK,
                    rollback_reason=f"{reason} (compensation error: {e})",
                )
                return True

        self.persistence.update_workflow_status(
            workflow_id=workflow_id,
            status=WorkflowStatus.ROLLED_BACK,
            rollback_reason=reason,
        )
        logger.info("Workflow %s rolled back: %s", workflow_id, reason)
        return True

    def checkpoint_step(
        self,
        workflow_id: str,
        step_id: str,
        step_name: str,
        capability_id: str,
        agent_name: str,
        status: str,
        execution_order: int,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """
        Checkpoint a step execution to database.

        This is called after every step execution to enable crash recovery.
        """
        self.persistence.checkpoint_step(
            workflow_id=workflow_id,
            step_id=step_id,
            step_name=step_name,
            capability_id=capability_id,
            agent_name=agent_name,
            status=status,
            execution_order=execution_order,
            inputs=inputs,
            outputs=outputs,
            error_message=error_message
        )

    def checkpoint_compensation(
        self,
        workflow_id: str,
        step_id: str,
        intent: CompensationIntent
    ):
        """
        Checkpoint a compensation intent to database.

        This is called when a step completes successfully and creates an undo closure.
        """
        self.persistence.log_compensation(
            workflow_id=workflow_id,
            step_id=step_id,
            intent=intent
        )
