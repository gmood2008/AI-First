"""
Workflow Persistence Layer for AI-First Runtime v3.0

Provides crash recovery and stateful workflow execution:
- SQLite persistence for workflow state
- Checkpointing after every step
- Compensation log serialization
- Auto-resume on restart
"""
import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from enum import Enum

from ..types import ExecutionContext


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class CompensationIntent:
    """
    Serializable representation of an undo operation.

    Instead of storing Python closures (which can't be pickled reliably),
    we store the *intent* of the compensation action.
    """

    def __init__(
        self,
        action: str,
        capability_id: str,
        params: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize compensation intent.

        Args:
            action: Type of compensation (e.g., "delete", "restore", "revert")
            capability_id: Capability that created this resource
            params: Parameters needed to undo (e.g., {"path": "/tmp/file.txt"})
            metadata: Additional context (e.g., original file content for restore)
        """
        self.action = action
        self.capability_id = capability_id
        self.params = params
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "action": self.action,
            "capability_id": self.capability_id,
            "params": self.params,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompensationIntent':
        """Deserialize from dictionary."""
        return cls(
            action=data["action"],
            capability_id=data["capability_id"],
            params=data["params"],
            metadata=data.get("metadata", {})
        )


class WorkflowPersistence:
    """
    Workflow persistence manager.

    Extends audit.db with workflow-specific tables for crash recovery.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize workflow persistence.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.ai-first/audit.db
        """
        if db_path is None:
            db_path = os.path.expanduser('~/.ai-first/audit.db')

        self.db_path = db_path
        self._ensure_db_directory()
        self._init_schema()

    def _ensure_db_directory(self):
        """Create database directory if it doesn't exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    def _init_schema(self):
        """Initialize workflow persistence schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode=WAL")

        # Create workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                owner TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                spec_yaml TEXT NOT NULL,
                context_json TEXT,
                error_message TEXT,
                rollback_reason TEXT
            )
        """)

        # Create workflow_steps table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                step_name TEXT NOT NULL,
                capability_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                inputs_json TEXT,
                outputs_json TEXT,
                error_message TEXT,
                execution_order INTEGER NOT NULL,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
            )
        """)

        # Create compensation_log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compensation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                compensation_intent_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                executed_at TEXT,
                status TEXT NOT NULL,
                error_message TEXT,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_workflow_steps_workflow_id ON workflow_steps(workflow_id)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_compensation_log_workflow_id ON compensation_log(workflow_id)")

        conn.commit()
        conn.close()

        # Set file permissions (readable only by user)
        os.chmod(self.db_path, 0o600)

    def create_workflow(
        self,
        workflow_id: str,
        name: str,
        owner: str,
        spec_yaml: str,
        context: Optional[ExecutionContext] = None
    ) -> None:
        """
        Create a new workflow record.

        Args:
            workflow_id: Unique workflow identifier
            name: Workflow name
            owner: Workflow owner (agent name)
            spec_yaml: Original workflow YAML specification
            context: Execution context (optional)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()
        context_json = json.dumps(
            self._serialize_context(context)) if context else None

        cursor.execute("""
            INSERT INTO workflows (
                id, name, owner, status, created_at, updated_at,
                spec_yaml, context_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            workflow_id,
            name,
            owner,
            WorkflowStatus.PENDING.value,
            now,
            now,
            spec_yaml,
            context_json
        ))

        conn.commit()
        conn.close()

    def update_workflow_status(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        error_message: Optional[str] = None,
        rollback_reason: Optional[str] = None
    ) -> None:
        """
        Update workflow status.

        Args:
            workflow_id: Workflow identifier
            status: New status
            error_message: Error message (if failed)
            rollback_reason: Reason for rollback (if rolled back)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        updates = {
            "status": status.value,
            "updated_at": now
        }

        if status == WorkflowStatus.RUNNING:
            updates["started_at"] = now
        elif status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.ROLLED_BACK):
            updates["completed_at"] = now

        if error_message:
            updates["error_message"] = error_message
        if rollback_reason:
            updates["rollback_reason"] = rollback_reason

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [workflow_id]

        cursor.execute(f"""
            UPDATE workflows
            SET {set_clause}
            WHERE id = ?
        """, values)

        conn.commit()
        conn.close()

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
    ) -> None:
        """
        Checkpoint a workflow step execution.

        Args:
            workflow_id: Workflow identifier
            step_id: Step identifier
            step_name: Step name
            capability_id: Capability being executed
            agent_name: Agent executing the step
            status: Step status (running, completed, failed)
            execution_order: Order of execution
            inputs: Step inputs
            outputs: Step outputs
            error_message: Error message (if failed)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        # Check if step already exists
        cursor.execute("""
            SELECT id FROM workflow_steps
            WHERE workflow_id = ? AND step_id = ?
        """, (workflow_id, step_id))

        existing = cursor.fetchone()

        if existing:
            # Update existing step
            updates = {
                "status": status,
                "outputs_json": json.dumps(outputs) if outputs else None,
                "error_message": error_message
            }

            if status == "completed":
                updates["completed_at"] = now

            set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
            values = list(updates.values()) + [workflow_id, step_id]

            cursor.execute(f"""
                UPDATE workflow_steps
                SET {set_clause}
                WHERE workflow_id = ? AND step_id = ?
            """, values)
        else:
            # Insert new step
            cursor.execute("""
                INSERT INTO workflow_steps (
                    workflow_id, step_id, step_name, capability_id, agent_name,
                    status, started_at, inputs_json, execution_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow_id,
                step_id,
                step_name,
                capability_id,
                agent_name,
                status,
                now,
                json.dumps(inputs) if inputs else None,
                execution_order
            ))

        conn.commit()
        conn.close()

    def log_compensation(
        self,
        workflow_id: str,
        step_id: str,
        intent: CompensationIntent
    ) -> None:
        """
        Log a compensation intent to the compensation stack.

        Args:
            workflow_id: Workflow identifier
            step_id: Step that created this compensation
            intent: Compensation intent
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()

        cursor.execute("""
            INSERT INTO compensation_log (
                workflow_id, step_id, compensation_intent_json,
                created_at, status
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            workflow_id,
            step_id,
            json.dumps(intent.to_dict()),
            now,
            "pending"
        ))

        conn.commit()
        conn.close()

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve workflow record.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Workflow record or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM workflows WHERE id = ?
        """, (workflow_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_running_workflows(self) -> List[Dict[str, Any]]:
        """
        Get all workflows in RUNNING or PAUSED state.

        Returns:
            List of workflow records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM workflows
            WHERE status IN (?, ?)
            ORDER BY created_at ASC
        """, (WorkflowStatus.RUNNING.value, WorkflowStatus.PAUSED.value))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_workflow_steps(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get all steps for a workflow.

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of step records
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM workflow_steps
            WHERE workflow_id = ?
            ORDER BY execution_order ASC
        """, (workflow_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_compensation_stack(
            self, workflow_id: str) -> List[CompensationIntent]:
        """
        Get compensation stack for a workflow (LIFO order).

        Args:
            workflow_id: Workflow identifier

        Returns:
            List of compensation intents (most recent first)
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM compensation_log
            WHERE workflow_id = ? AND status = 'pending'
            ORDER BY id DESC
        """, (workflow_id,))

        rows = cursor.fetchall()
        conn.close()

        return [
            CompensationIntent.from_dict(json.loads(row["compensation_intent_json"]))
            for row in rows
        ]

    def mark_compensation_executed(
        self,
        workflow_id: str,
        intent: CompensationIntent,
        error_message: Optional[str] = None
    ) -> None:
        """
        Mark a compensation as executed.

        Args:
            workflow_id: Workflow identifier
            intent: Compensation intent that was executed
            error_message: Error message (if failed)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        now = datetime.utcnow().isoformat()
        status = "failed" if error_message else "executed"

        cursor.execute("""
            UPDATE compensation_log
            SET executed_at = ?, status = ?, error_message = ?
            WHERE workflow_id = ?
              AND compensation_intent_json = ?
              AND status = 'pending'
            ORDER BY id DESC
            LIMIT 1
        """, (
            now,
            status,
            error_message,
            workflow_id,
            json.dumps(intent.to_dict())
        ))

        conn.commit()
        conn.close()

    def _serialize_context(
            self, context: Optional[ExecutionContext]) -> Dict[str, Any]:
        """Serialize ExecutionContext to JSON-compatible dict."""
        if not context:
            return {}

        return {
            "session_id": context.session_id,
            "user_id": context.user_id,
            "workspace_root": str(context.workspace_root),
            "metadata": context.metadata
        }
