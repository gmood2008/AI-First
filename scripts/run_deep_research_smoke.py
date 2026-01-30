#!/usr/bin/env python3

import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from runtime.audit import AuditLogger
from runtime.engine import RuntimeEngine
from runtime.registry import CapabilityRegistry
from runtime.stdlib.loader import load_stdlib
from runtime.types import ExecutionContext
from runtime.undo.manager import UndoManager
from runtime.mcp.specs_resolver import resolve_specs_dir

from runtime.workflow.engine import WorkflowEngine, WorkflowStatus
from runtime.workflow.persistence import WorkflowPersistence
from runtime.workflow.spec_loader import load_workflow_spec_by_id


def main():
    run_id = uuid.uuid4().hex
    workspace = Path.cwd() / "workspace" / run_id
    workspace.mkdir(parents=True, exist_ok=True)

    specs_dir = REPO_ROOT / "capabilities" / "validated" / "stdlib"
    registry = CapabilityRegistry()
    load_stdlib(registry, specs_dir)

    backup_dir = workspace / ".ai-first" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    undo_manager = UndoManager(backup_dir)

    audit_db_path = workspace / ".ai-first" / "audit.db"
    audit_db_path.parent.mkdir(parents=True, exist_ok=True)
    audit_logger = AuditLogger(str(audit_db_path))

    runtime_engine = RuntimeEngine(registry, undo_manager=undo_manager, audit_logger=audit_logger)

    context = ExecutionContext(
        user_id="smoke_user",
        workspace_root=workspace,
        session_id=f"smoke_{run_id}",
        confirmation_callback=lambda _msg, _details: True,
        undo_enabled=True,
    )

    spec = load_workflow_spec_by_id("deep_research_financial_report")
    spec.initial_state["run_id"] = run_id
    spec.initial_state["session_id"] = context.session_id

    workflow_engine = WorkflowEngine(
        runtime_engine=runtime_engine,
        execution_context=context,
        persistence=WorkflowPersistence(str(audit_db_path)),
        pack_registry=None,
    )

    workflow_id = workflow_engine.submit_workflow(spec)
    workflow_engine.start_workflow(workflow_id)

    wf_ctx = workflow_engine.workflows[workflow_id]
    if wf_ctx.spec.metadata.status == WorkflowStatus.PAUSED:
        workflow_engine.resume_workflow(workflow_id, decision="approve", approver=context.user_id)

    wf_ctx = workflow_engine.workflows[workflow_id]
    print(str(wf_ctx.spec.metadata.status.value))


if __name__ == "__main__":
    main()
