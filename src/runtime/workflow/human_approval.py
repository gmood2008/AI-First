"""
Human-in-the-Loop Module for AI-First Runtime v3.0

Provides webhook-based human approval for workflow steps:
- Send approval requests to configured webhook URL
- Pause workflow execution until decision received
- Support approve/reject via CLI or API
"""
import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class HumanApprovalManager:
    """
    Manages human approval requests for workflow steps.

    When a workflow step requires human approval, this manager:
    1. Pauses the workflow
    2. Sends a webhook notification
    3. Waits for approval decision
    4. Resumes or cancels the workflow
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize human approval manager.

        Args:
            webhook_url: URL to send approval requests to.
                        Can also be set via AI_FIRST_APPROVAL_WEBHOOK env var.
        """
        self.webhook_url = webhook_url or os.getenv(
            "AI_FIRST_APPROVAL_WEBHOOK")
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

    def request_approval(
        self,
        workflow_id: str,
        step_id: str,
        step_name: str,
        step_info: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        Request human approval for a workflow step.

        Args:
            workflow_id: Workflow identifier
            step_id: Step identifier
            step_name: Human-readable step name
            step_info: Step details (capability, inputs, risk level)
            context: Workflow context

        Returns:
            approval_id: Unique identifier for this approval request
        """
        approval_id = f"{workflow_id}:{step_id}"

        # Store pending approval
        self.pending_approvals[approval_id] = {
            "workflow_id": workflow_id,
            "step_id": step_id,
            "step_name": step_name,
            "step_info": step_info,
            "context": context,
            "requested_at": datetime.utcnow().isoformat(),
            "status": "pending"
        }

        # Send webhook notification
        if self.webhook_url:
            self._send_webhook(
                approval_id,
                workflow_id,
                step_id,
                step_name,
                step_info)
        else:
            logger.warning(
                f"No webhook URL configured. Approval request logged but not sent.")
            logger.info(
                f"To approve: airun workflow resume {workflow_id} --decision approve")
            logger.info(
                f"To reject: airun workflow resume {workflow_id} --decision reject")

        return approval_id

    def _send_webhook(
        self,
        approval_id: str,
        workflow_id: str,
        step_id: str,
        step_name: str,
        step_info: Dict[str, Any]
    ):
        """
        Send webhook notification for approval request.

        Args:
            approval_id: Approval identifier
            workflow_id: Workflow identifier
            step_id: Step identifier
            step_name: Step name
            step_info: Step details
        """
        try:
            payload = {
                "event": "approval_required",
                "approval_id": approval_id,
                "workflow_id": workflow_id,
                "step_id": step_id,
                "step_name": step_name,
                "step_info": step_info,
                "requested_at": datetime.utcnow().isoformat(),
                "actions": {
                    "approve": f"airun workflow resume {workflow_id} --decision approve",
                    "reject": f"airun workflow resume {workflow_id} --decision reject"}}

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                logger.info(
                    f"Approval request sent to webhook: {self.webhook_url}")
            else:
                logger.error(
                    f"Webhook returned status {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send webhook: {e}")

    def record_decision(
        self,
        workflow_id: str,
        decision: str,
        approver: Optional[str] = None
    ) -> bool:
        """
        Record an approval decision.

        Args:
            workflow_id: Workflow identifier
            decision: "approve" or "reject"
            approver: Who made the decision (optional)

        Returns:
            True if decision was recorded, False if no pending approval found
        """
        # Find pending approval for this workflow
        approval_id = None
        for aid, approval in self.pending_approvals.items():
            if approval["workflow_id"] == workflow_id and approval["status"] == "pending":
                approval_id = aid
                break

        if not approval_id:
            logger.warning(
                f"No pending approval found for workflow {workflow_id}")
            return False

        # Record decision
        self.pending_approvals[approval_id]["status"] = decision
        self.pending_approvals[approval_id]["decided_at"] = datetime.utcnow(
        ).isoformat()
        self.pending_approvals[approval_id]["approver"] = approver or "unknown"

        logger.info(f"Approval decision recorded: {decision} by {approver}")
        return True

    def get_decision(self, workflow_id: str) -> Optional[str]:
        """
        Get the approval decision for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            "approve", "reject", or None if still pending
        """
        for approval in self.pending_approvals.values():
            if approval["workflow_id"] == workflow_id:
                status = approval["status"]
                if status in ("approve", "reject"):
                    return status
        return None

    def is_pending(self, workflow_id: str) -> bool:
        """
        Check if a workflow has a pending approval.

        Args:
            workflow_id: Workflow identifier

        Returns:
            True if approval is pending
        """
        for approval in self.pending_approvals.values():
            if approval["workflow_id"] == workflow_id and approval["status"] == "pending":
                return True
        return False

    def clear_approval(self, workflow_id: str):
        """
        Clear approval records for a workflow.

        Args:
            workflow_id: Workflow identifier
        """
        to_remove = [
            aid for aid, approval in self.pending_approvals.items()
            if approval["workflow_id"] == workflow_id
        ]
        for aid in to_remove:
            del self.pending_approvals[aid]
