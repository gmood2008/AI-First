"""
AI-First Runtime CLI - Command-line interface for testing and execution.

This provides a user-friendly CLI for interacting with the runtime.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import uuid
from pathlib import Path
import contextlib
import io
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

import click
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from runtime.types import (
    ExecutionContext,
    ValidationError,
    SecurityError,
    ConfirmationDeniedError,
    CapabilityNotFoundError,
)
from runtime.registry import CapabilityRegistry, SkillFacadeRegistry
from runtime.engine import RuntimeEngine
from runtime.undo.manager import UndoManager
from runtime.stdlib.loader import load_stdlib, get_stdlib_info
from runtime.external_loader import load_external_capabilities
from runtime.facade_loader import load_facades_from_directory
from runtime.facade_router import resolve_and_validate
from runtime.pack_loader import load_packs_from_directory
from runtime.audit import AuditLogger
from runtime.paths import facades_dir as resolve_facades_dir, packs_dir as resolve_packs_dir, external_specs_dir as resolve_external_dir

from registry.pack_registry import PackRegistry
from runtime.workflow.engine import WorkflowEngine
from runtime.workflow.engine import GovernanceDecision
from runtime.workflow.persistence import WorkflowPersistence
from runtime.workflow.spec_loader import load_workflow_spec_by_id
from runtime.workflow.governance_http import GovernanceHttpConfig, build_http_governance_hooks
from specs.v3.workflow_schema import WorkflowSpec
from runtime.mcp.specs_resolver import resolve_specs_dir

console = Console()


@contextlib.contextmanager
def _bridge_silence(enabled: bool):
    if not enabled:
        yield
        return

    import logging
    import tempfile

    old_disable = logging.root.manager.disable
    logging.disable(logging.CRITICAL)

    try:
        sys.stdout.flush()
    except Exception:
        pass
    try:
        sys.stderr.flush()
    except Exception:
        pass

    out_fd = 1
    err_fd = 2
    saved_out = os.dup(out_fd)
    saved_err = os.dup(err_fd)
    try:
        with tempfile.TemporaryFile(mode="w+") as tmp:
            os.dup2(tmp.fileno(), out_fd)
            os.dup2(tmp.fileno(), err_fd)
            yield
    finally:
        try:
            os.dup2(saved_out, out_fd)
            os.dup2(saved_err, err_fd)
        finally:
            os.close(saved_out)
            os.close(saved_err)
            logging.disable(old_disable)

        try:
            sys.stdout.flush()
        except Exception:
            pass
        try:
            sys.stderr.flush()
        except Exception:
            pass


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _fail(message: str, code: int = 2) -> None:
    console.print(f"[red]{message}[/red]")
    raise SystemExit(code)


def _print_json(payload: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _fail_json(payload: Dict[str, Any], code: int) -> None:
    _print_json(payload)
    raise SystemExit(code)


def _parse_json_arg(value: Optional[str], *, name: str) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except Exception as e:
        _fail(f"Invalid JSON for {name}: {e}", code=2)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _map_failure_category(exc: BaseException | None, *, execution_result: Any | None = None) -> str:
    if execution_result is not None and getattr(execution_result, "status", None) is not None:
        status_value = getattr(execution_result.status, "value", str(execution_result.status))
        if status_value in {"denied", "DENIED"}:
            return "PERMISSION_DENIED"

    if exc is None:
        return "UNKNOWN_ERROR"

    if isinstance(exc, ValidationError):
        return "VALIDATION_ERROR"
    if isinstance(exc, (SecurityError, ConfirmationDeniedError)):
        return "PERMISSION_DENIED"
    if isinstance(exc, CapabilityNotFoundError):
        return "RESOURCE_NOT_FOUND"
    if isinstance(exc, TimeoutError):
        return "TIMEOUT"

    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if "timeout" in name or "timeout" in msg:
        return "TIMEOUT"
    if "permission" in msg or "denied" in msg or "forbidden" in msg:
        return "PERMISSION_DENIED"
    if "not found" in msg or "no such file" in msg:
        return "RESOURCE_NOT_FOUND"
    if "network" in msg or "connection" in msg:
        return "NETWORK_ERROR"
    return "INTERNAL_ERROR"


def _map_exit_code(category: str) -> int:
    mapping = {
        "VALIDATION_ERROR": 10,
        "PERMISSION_DENIED": 11,
        "SECURITY_VIOLATION": 12,
        "CAPABILITY_NOT_FOUND": 13,
        "CONFIRMATION_DENIED": 14,
        "TIMEOUT": 15,
        "CANCELLED": 16,
        "PAUSED": 30,
        "INTERNAL_ERROR": 20,
    }
    return mapping.get(category, 20)


def _load_workflow_spec_from_path(path: Path) -> WorkflowSpec:
    if not path.exists():
        _fail(f"Workflow spec file not found: {path}", code=4)

    suffix = path.suffix.lower()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except Exception as e:
        _fail(f"Failed to read workflow spec file: {path} ({e})", code=2)

    try:
        if suffix in {".yaml", ".yml"}:
            raw = yaml.safe_load(raw_text)
        else:
            raw = json.loads(raw_text)
    except Exception as e:
        _fail(f"Workflow spec parse failed: {path} ({e})", code=2)

    if not isinstance(raw, dict):
        _fail(f"Workflow spec must be a JSON/YAML object: {path}", code=2)

    # Accept both pack-style workflow yaml and v3 WorkflowSpec dict.
    metadata = raw.get("metadata") or {}
    if not isinstance(metadata, dict):
        _fail(f"workflow spec metadata must be an object: {path}", code=2)

    if "steps" in raw and "name" in raw and "metadata" in raw:
        spec_dict = raw
    else:
        workflow_id = raw.get("workflow_id")
        if workflow_id and "workflow_id" not in metadata:
            metadata = {**metadata, "workflow_id": workflow_id}

        spec_dict = {
            "name": raw.get("name") or workflow_id,
            "version": raw.get("version", "1.0.0"),
            "description": raw.get("description", ""),
            "steps": raw.get("steps", []),
            "initial_state": raw.get("initial_state", {}),
            "metadata": metadata,
            "policy": raw.get("policy", []),
            "global_compensation_steps": raw.get("global_compensation_steps", []),
            "max_execution_time_seconds": raw.get("max_execution_time_seconds", 3600),
            "enable_auto_rollback": raw.get("enable_auto_rollback", True),
        }

    try:
        return WorkflowSpec.model_validate(spec_dict)
    except Exception as e:
        _fail(f"Workflow spec validation failed: {e}", code=2)


def _workflow_status_to_bridge_status(status: Optional[str]) -> str:
    if status is None:
        return "unknown"
    raw_value = getattr(status, "value", status)
    value = str(raw_value).lower()
    if "." in value:
        # sqlite may have stored Enum objects via str(enum) => 'WorkflowStatus.PAUSED'
        value = value.split(".")[-1]
    if value in {"completed", "success", "succeeded"}:
        return "success"
    if value == "paused":
        return "paused"
    if value in {"failed", "error"}:
        return "failure"
    if value in {"rolled_back", "rolledback"}:
        return "rolled_back"
    return value


def _build_workflow_record(
    *,
    record_id: str,
    execution_id: str,
    trace_id: str,
    parent_trace_id: Optional[str],
    quest_id: Optional[str],
    user_id: str,
    persistence: WorkflowPersistence,
    workflow_execution_id: str,
    start_iso: str,
) -> tuple[Dict[str, Any], int]:
    wf_row = persistence.get_workflow(workflow_execution_id) or {}
    step_rows = persistence.get_workflow_steps(workflow_execution_id) or []

    def _normalize_status(value: Any) -> Any:
        if value is None:
            return None
        raw = getattr(value, "value", value)
        text = str(raw)
        if "." in text:
            text = text.split(".")[-1]
        return text.lower()

    def _safe_json_load(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return json.loads(value)
            except Exception:
                return value
        return value

    steps_payload: List[Dict[str, Any]] = []
    for r in step_rows:
        steps_payload.append(
            {
                "stepId": r.get("step_id"),
                "stepName": r.get("step_name"),
                "capabilityId": r.get("capability_id"),
                "agentName": r.get("agent_name"),
                "status": _normalize_status(r.get("status")),
                "startedAt": r.get("started_at"),
                "completedAt": r.get("completed_at"),
                "inputs": _safe_json_load(r.get("inputs_json")),
                "outputs": _safe_json_load(r.get("outputs_json")),
                "errorMessage": r.get("error_message"),
                "executionOrder": r.get("execution_order"),
            }
        )

    raw_status = wf_row.get("status")
    bridge_status = _workflow_status_to_bridge_status(raw_status)
    if bridge_status not in {"paused", "success", "failure", "rolled_back"}:
        for r in step_rows:
            step_status = r.get("status")
            step_status_value = getattr(step_status, "value", step_status)
            if str(step_status_value).lower() == "paused":
                bridge_status = "paused"
                break
    end_iso = _now_iso()

    failure_category: Optional[str] = None
    error_obj: Optional[Dict[str, Any]] = None
    exit_code = 0
    if bridge_status == "success":
        exit_code = 0
    elif bridge_status == "paused":
        failure_category = "PAUSED"
        error_obj = {
            "category": failure_category,
            "message": "Workflow paused (approval required)",
            "recoverable": True,
            "retryable": False,
        }
        exit_code = _map_exit_code(failure_category)
    elif bridge_status == "rolled_back":
        # Rollback is an explicit terminal control action; treat as a successful completion of rollback.
        exit_code = 0
    else:
        msg = wf_row.get("error_message") or "Workflow failed"
        msg_text = str(msg)
        if msg_text.strip().lower().startswith("cancelled"):
            failure_category = "CANCELLED"
        else:
            failure_category = _map_failure_category(RuntimeError(msg_text))
        error_obj = {
            "category": failure_category,
            "message": msg_text,
            "recoverable": False,
            "retryable": False,
        }
        exit_code = _map_exit_code(failure_category)

    payload: Dict[str, Any] = {
        "id": record_id,
        "executionId": execution_id,
        "traceId": trace_id,
        "parentTraceId": parent_trace_id,
        "questId": quest_id,
        "workflowExecutionId": workflow_execution_id,
        "workflowName": wf_row.get("name") or None,
        "status": bridge_status,
        "error": error_obj,
        "startTime": start_iso,
        "endTime": end_iso,
        "workflow": {
            "id": wf_row.get("id"),
            "name": wf_row.get("name"),
            "owner": wf_row.get("owner"),
            "status": _normalize_status(wf_row.get("status")),
            "createdAt": wf_row.get("created_at"),
            "updatedAt": wf_row.get("updated_at"),
            "startedAt": wf_row.get("started_at"),
            "completedAt": wf_row.get("completed_at"),
            "errorMessage": wf_row.get("error_message"),
            "rollbackReason": wf_row.get("rollback_reason"),
        },
        "steps": steps_payload,
        "userId": user_id,
        "metadata": {"failureCategory": failure_category} if failure_category else None,
    }

    return payload, exit_code


def _emit_workflow_record(
    *,
    record_id: str,
    execution_id: str,
    trace_id: str,
    parent_trace_id: Optional[str],
    quest_id: Optional[str],
    user_id: str,
    persistence: WorkflowPersistence,
    workflow_execution_id: str,
    schema: Optional[Dict[str, Any]],
    start_iso: str,
) -> None:
    payload, exit_code = _build_workflow_record(
        record_id=record_id,
        execution_id=execution_id,
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        quest_id=quest_id,
        user_id=user_id,
        persistence=persistence,
        workflow_execution_id=workflow_execution_id,
        start_iso=start_iso,
    )

    if schema is not None:
        schema_error = _validate_json_with_schema(payload, schema)
        if schema_error is not None:
            category = "VALIDATION_ERROR"
            payload = {
                **payload,
                "status": "failure",
                "error": {
                    "category": category,
                    "message": f"Bridge output schema validation failed: {schema_error}",
                    "recoverable": False,
                    "retryable": False,
                },
            }
            _print_json(payload)
            raise SystemExit(_map_exit_code(category))

    _print_json(payload)
    raise SystemExit(exit_code)


def _load_json_schema(schema_path: Path) -> Dict[str, Any]:
    try:
        raw = schema_path.read_text(encoding="utf-8")
    except Exception as e:
        _fail(f"Failed to read schema file: {schema_path} ({e})", code=2)
    try:
        parsed = json.loads(raw)
    except Exception as e:
        _fail(f"Schema is not valid JSON: {schema_path} ({e})", code=2)
    if not isinstance(parsed, dict):
        _fail(f"Schema JSON must be an object: {schema_path}", code=2)
    return parsed


def _validate_json_with_schema(payload: Dict[str, Any], schema: Dict[str, Any]) -> Optional[str]:
    try:
        import jsonschema  # type: ignore
    except Exception:
        return "jsonschema is not installed"

    try:
        jsonschema.validate(instance=payload, schema=schema)
        return None
    except Exception as e:
        return str(e)


def _forbidden(message: str) -> None:
    _fail(f"FORBIDDEN: {message}")


def _parse_kv_inputs(pairs: Tuple[str, ...]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for p in pairs:
        if "=" not in p:
            _fail(f"Invalid --input '{p}', expected key=value")
        k, v = p.split("=", 1)
        k = k.strip()
        if not k:
            _fail(f"Invalid --input '{p}', empty key")
        result[k] = v
    return result


def _build_facade_runtime(workspace: Path, *, quiet: bool = False):
    specs_dir = resolve_specs_dir()

    registry = CapabilityRegistry()
    if quiet:
        _sink = io.StringIO()
        redirect = contextlib.ExitStack()
        redirect.enter_context(contextlib.redirect_stdout(_sink))
        redirect.enter_context(contextlib.redirect_stderr(_sink))
        global console
        _old_console = console
        console = Console(file=_sink, force_terminal=False)
        redirect.callback(lambda: _restore_console(_old_console))

        import logging

        old_disable = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        redirect.callback(lambda: logging.disable(old_disable))

        root_logger = logging.getLogger()
        _old_handlers = list(root_logger.handlers)
        _old_propagate = root_logger.propagate
        _old_level = root_logger.level

        root_logger.handlers = [logging.NullHandler()]
        root_logger.propagate = False
        root_logger.setLevel(logging.CRITICAL + 1)

        def _restore_logging_handlers() -> None:
            root_logger.handlers = _old_handlers
            root_logger.propagate = _old_propagate
            root_logger.setLevel(_old_level)

        redirect.callback(_restore_logging_handlers)
    else:
        redirect = contextlib.nullcontext()

    def _restore_console(prev: Console) -> None:
        global console
        console = prev

    with redirect:
        load_stdlib(registry, specs_dir)
        external_dir = resolve_external_dir()
        load_external_capabilities(registry, external_dir)
    backup_dir = workspace / ".ai-first" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    undo_manager = UndoManager(backup_dir)

    audit_db_path = workspace / ".ai-first" / "audit.db"
    audit_db_path.parent.mkdir(parents=True, exist_ok=True)
    audit_logger = AuditLogger(str(audit_db_path))

    engine = RuntimeEngine(registry, undo_manager=undo_manager, audit_logger=audit_logger)

    facade_registry = SkillFacadeRegistry()
    facades_dir = resolve_facades_dir()
    with redirect:
        load_facades_from_directory(facade_registry, facades_dir, activate=False, registered_by="cli")

    pack_registry_db = workspace / ".ai-first" / "pack_registry.db"
    pack_registry_db.parent.mkdir(parents=True, exist_ok=True)
    pack_registry = PackRegistry(db_path=pack_registry_db, capability_registry=None)
    packs_dir = resolve_packs_dir()
    with redirect:
        load_packs_from_directory(pack_registry, packs_dir, activate=True, registered_by="cli")

    return specs_dir, engine, facade_registry, pack_registry, audit_logger


def _find_pack_for_workflow(pack_registry: PackRegistry, workflow_id: str):
    from specs.capability_pack import PackState

    for p in pack_registry.list_packs(state=PackState.ACTIVE):
        if workflow_id in (p.includes.workflows or []):
            return p
    return None


def _print_route_status(
    facade_registry: SkillFacadeRegistry,
    pack_registry: PackRegistry,
    facade_name: str,
    route_type: str,
    ref: str,
    allowed_workflows: Optional[List[str]],
    json_output: bool,
) -> Dict[str, Any]:
    facade_state = facade_registry.get_facade_state(facade_name)

    pack = None
    if route_type == "workflow":
        pack = _find_pack_for_workflow(pack_registry, ref)
    elif route_type == "pack":
        pack = pack_registry.get_pack(ref)
        if pack is None:
            from specs.capability_pack import PackState

            for p in pack_registry.list_packs(state=PackState.ACTIVE, pack_name=ref):
                pack = p
                break

    pack_state = None
    if pack is not None:
        pack_state = pack_registry.get_pack_state(pack.pack_id, pack.version)

    payload: Dict[str, Any] = {
        "facade": {
            "name": facade_name,
            "state": facade_state.value if facade_state else None,
        },
        "route": {
            "type": route_type,
            "ref": ref,
            "allowed_workflows": allowed_workflows or [],
        },
        "pack": None,
    }
    if pack is not None:
        payload["pack"] = {
            "pack_id": pack.pack_id,
            "pack_name": pack.name,
            "state": pack_state.value if pack_state else None,
            "max_risk": pack.risk_profile.max_risk.value,
            "requires_human_approval": bool(pack.risk_profile.requires_human_approval),
        }

    if not json_output:
        table = Table(title="Facade Resolution")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        table.add_row("facade", facade_name)
        table.add_row("facade_state", facade_state.value if facade_state else "UNKNOWN")
        table.add_row("route_type", route_type)
        table.add_row("ref", ref)
        if pack is not None:
            table.add_row("pack_id", pack.pack_id)
            table.add_row("pack_name", pack.name)
            table.add_row("pack_state", pack_state.value if pack_state else "UNKNOWN")
            table.add_row("pack_max_risk", pack.risk_profile.max_risk.value)
            table.add_row(
                "pack_requires_human_approval",
                "true" if pack.risk_profile.requires_human_approval else "false",
            )
        if allowed_workflows is not None:
            table.add_row("allowed_workflows", ", ".join(allowed_workflows) if allowed_workflows else "")
        console.print(table)

    return payload


def _governance_gate_or_exit(pack) -> Optional[Dict[str, Any]]:
    if pack is not None and getattr(pack, "risk_profile", None) is not None:
        if pack.risk_profile.requires_human_approval:
            return {
                "error": {
                    "type": "approval_required",
                    "message": "Approval required by pack risk profile. Execution blocked (no bypass from CLI).",
                },
                "pack": {
                    "pack_id": pack.pack_id,
                    "pack_name": pack.name,
                    "max_risk": pack.risk_profile.max_risk.value,
                    "requires_human_approval": True,
                },
            }
    return None


def confirmation_callback(message: str, params: dict) -> bool:
    """
    CLI confirmation callback.
    
    Shows confirmation message and waits for user input.
    """
    console.print(Panel(message, title="⚠️  Confirmation Required", border_style="yellow"))
    
    response = click.confirm("Proceed with this operation?", default=False)
    return response


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """
    AI-First Runtime - Execute capability specs safely with undo support.
    
    This CLI allows you to execute capabilities, manage undo history,
    and inspect the runtime state.
    """
    pass


@cli.command("nl")
@click.argument("user_intent")
@click.option("--json", "json_output", is_flag=True)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
    help="Workspace directory for operations",
)
def nl(user_intent: str, json_output: bool, workspace: Path):
    workspace.mkdir(parents=True, exist_ok=True)

    _, runtime_engine, facade_registry, pack_registry, audit_logger = _build_facade_runtime(workspace, quiet=True)

    route = resolve_and_validate(user_intent, facade_registry, pack_registry)
    if route is None:
        if json_output:
            _fail_json(
                {
                    "error": {
                        "type": "no_facade_match",
                        "message": "No ACTIVE facade matched the given intent.",
                    },
                    "intent": user_intent,
                },
                code=4,
            )
        _fail("No ACTIVE facade matched the given intent.", code=4)

    status = _print_route_status(
        facade_registry=facade_registry,
        pack_registry=pack_registry,
        facade_name=route.facade.name,
        route_type=route.route_type,
        ref=route.ref,
        allowed_workflows=route.allowed_workflows,
        json_output=json_output,
    )

    if route.route_type == "pack":
        audit_logger.log_action(
            session_id=f"cli_{uuid.uuid4().hex}",
            user_id="cli_user",
            capability_id=f"facade:{route.facade.name}",
            action_type="resolve_pack",
            params={"intent": user_intent, "pack_ref": route.ref},
            result={"allowed_workflows": route.allowed_workflows or []},
            status="success",
        )
        if json_output:
            _print_json({"status": "pack_resolved", **status})
        return

    if route.route_type != "workflow":
        _fail(f"Unsupported route_type: {route.route_type}")

    pack = _find_pack_for_workflow(pack_registry, route.ref)
    gate = _governance_gate_or_exit(pack)
    if gate is not None:
        if json_output:
            _fail_json({"status": "blocked", **status, **gate}, code=3)
        _fail(str(gate["error"]["message"]), code=3)

    spec = load_workflow_spec_by_id(route.ref)
    context = ExecutionContext(
        user_id="cli_user",
        workspace_root=workspace,
        session_id=f"cli_{uuid.uuid4().hex}",
        confirmation_callback=confirmation_callback,
        undo_enabled=True,
    )

    workflow_engine = WorkflowEngine(
        runtime_engine=runtime_engine,
        execution_context=context,
        persistence=WorkflowPersistence(str(workspace / ".ai-first" / "audit.db")),
        pack_registry=pack_registry,
    )

    workflow_id = workflow_engine.submit_workflow(spec)
    workflow_engine.start_workflow(workflow_id)

    audit_logger.log_action(
        session_id=context.session_id,
        user_id=context.user_id,
        capability_id=f"facade:{route.facade.name}",
        action_type="start_workflow",
        params={"intent": user_intent, "workflow": route.ref},
        result={"workflow_id": workflow_id},
        status="success",
    )
    if json_output:
        _print_json({"status": "workflow_started", **status, "workflow_id": workflow_id})
        return
    console.print(f"[green]Started workflow[/green]: {workflow_id}")


@cli.group("governance")
def governance_group():
    pass


@cli.group("bridge")
def bridge_group():
    pass


@bridge_group.command("exec-capability")
@click.option("--execution-id", required=True)
@click.option("--trace-id", required=True)
@click.option("--parent-trace-id")
@click.option("--user-id", required=True)
@click.option("--capability-id", required=True)
@click.option("--capability-name", required=True)
@click.option("--input-json", required=True)
@click.option("--metadata-json")
@click.option(
    "--schema-path",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=None,
    help="Optional JSON Schema file for validating the emitted JSON payload.",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
)
def bridge_exec_capability(
    execution_id: str,
    trace_id: str,
    parent_trace_id: Optional[str],
    user_id: str,
    capability_id: str,
    capability_name: str,
    input_json: str,
    metadata_json: Optional[str],
    schema_path: Optional[Path],
    workspace: Path,
):
    workspace.mkdir(parents=True, exist_ok=True)

    input_payload = _parse_json_arg(input_json, name="--input-json")
    metadata_payload = _parse_json_arg(metadata_json, name="--metadata-json")
    if not isinstance(input_payload, dict):
        _fail("--input-json must be a JSON object", code=2)

    record_id = uuid.uuid4().hex
    start_iso = _now_iso()

    schema_from_env = os.getenv("AEGIS_EXECUTION_RECORD_SCHEMA")
    effective_schema_path = schema_path
    if effective_schema_path is None and schema_from_env:
        effective_schema_path = Path(schema_from_env)
    schema: Optional[Dict[str, Any]] = None
    if effective_schema_path is not None:
        schema = _load_json_schema(effective_schema_path)

    _, runtime_engine, _, _, _ = _build_facade_runtime(workspace, quiet=True)

    context = ExecutionContext(
        user_id=user_id,
        workspace_root=workspace,
        session_id=f"aegis_{trace_id}",
        confirmation_callback=lambda _prompt, _meta: True,
        undo_enabled=True,
    )
    context.metadata.update({"traceId": trace_id})
    if parent_trace_id:
        context.metadata.update({"parentTraceId": parent_trace_id})

    try:
        result = runtime_engine.execute(
            capability_id=capability_name,
            params=input_payload,
            context=context,
        )

        end_iso = _now_iso()
        status_value = getattr(result.status, "value", str(result.status))

        if status_value == "success":
            status = "success"
            error_obj = None
            code = 0
        elif status_value in {"failed", "error"}:
            status = "failure"
            category = _map_failure_category(None, execution_result=result)
            error_obj = {
                "category": category,
                "message": result.error_message or "Execution failed",
                "recoverable": False,
                "retryable": False,
            }
            code = _map_exit_code(category)
        elif status_value == "denied":
            status = "failure"
            category = "PERMISSION_DENIED"
            error_obj = {
                "category": category,
                "message": result.error_message or "User denied confirmation",
                "recoverable": True,
                "retryable": False,
            }
            code = _map_exit_code(category)
        else:
            status = "failure"
            category = "UNKNOWN_ERROR"
            error_obj = {
                "category": category,
                "message": result.error_message or f"Unknown execution status: {status_value}",
                "recoverable": False,
                "retryable": False,
            }
            code = _map_exit_code(category)

        payload = {
            "id": record_id,
            "executionId": execution_id,
            "traceId": trace_id,
            "parentTraceId": parent_trace_id,
            "capabilityId": capability_id,
            "capabilityName": capability_name,
            "input": input_payload,
            "output": result.outputs if status == "success" else None,
            "status": status,
            "error": error_obj,
            "startTime": start_iso,
            "endTime": end_iso,
            "durationMs": float(getattr(result, "execution_time_ms", 0.0)),
            "userId": user_id,
            "metadata": metadata_payload if isinstance(metadata_payload, dict) else None,
        }

        if schema is not None:
            schema_error = _validate_json_with_schema(payload, schema)
            if schema_error is not None:
                category = "VALIDATION_ERROR"
                payload = {
                    **payload,
                    "status": "failure",
                    "output": None,
                    "error": {
                        "category": category,
                        "message": f"Bridge output schema validation failed: {schema_error}",
                        "recoverable": False,
                        "retryable": False,
                    },
                }
                _print_json(payload)
                raise SystemExit(_map_exit_code(category))

        _print_json(payload)
        raise SystemExit(code)

    except SystemExit:
        raise
    except BaseException as e:
        end_iso = _now_iso()
        category = _map_failure_category(e)
        payload = {
            "id": record_id,
            "executionId": execution_id,
            "traceId": trace_id,
            "parentTraceId": parent_trace_id,
            "capabilityId": capability_id,
            "capabilityName": capability_name,
            "input": input_payload,
            "output": None,
            "status": "failure" if category != "TIMEOUT" else "timeout",
            "error": {
                "category": category,
                "message": str(e),
                "details": None,
                "recoverable": False,
                "retryable": False,
            },
            "startTime": start_iso,
            "endTime": end_iso,
            "durationMs": None,
            "userId": user_id,
            "metadata": metadata_payload if isinstance(metadata_payload, dict) else None,
        }
        _print_json(payload)
        raise SystemExit(_map_exit_code(category))


@bridge_group.command("workflow-resume")
@click.option("--execution-id", required=True)
@click.option("--trace-id", required=True)
@click.option("--parent-trace-id")
@click.option("--quest-id")
@click.option("--user-id", required=True)
@click.option("--workflow-execution-id", required=True)
@click.option("--decision", type=click.Choice(["approve", "reject"]), required=True)
@click.option("--approver", default="aegis")
@click.option(
    "--schema-path",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=None,
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
)
def bridge_workflow_resume(
    execution_id: str,
    trace_id: str,
    parent_trace_id: Optional[str],
    quest_id: Optional[str],
    user_id: str,
    workflow_execution_id: str,
    decision: str,
    approver: str,
    schema_path: Optional[Path],
    workspace: Path,
):
    workspace.mkdir(parents=True, exist_ok=True)

    record_id = uuid.uuid4().hex
    start_iso = _now_iso()

    schema_from_env = os.getenv("AEGIS_WORKFLOW_RECORD_SCHEMA")
    effective_schema_path = schema_path
    if effective_schema_path is None and schema_from_env:
        effective_schema_path = Path(schema_from_env)
    schema: Optional[Dict[str, Any]] = None
    if effective_schema_path is not None:
        schema = _load_json_schema(effective_schema_path)

    with _bridge_silence(True):
        _, runtime_engine, _, pack_registry, _ = _build_facade_runtime(workspace, quiet=True)

    context = ExecutionContext(
        user_id=user_id,
        workspace_root=workspace,
        session_id=f"aegis_{trace_id}",
        confirmation_callback=lambda _prompt, _meta: True,
        undo_enabled=True,
    )
    context.metadata.update({"traceId": trace_id})
    if parent_trace_id:
        context.metadata.update({"parentTraceId": parent_trace_id})
    if quest_id:
        context.metadata.update({"questId": quest_id})

    persistence = WorkflowPersistence(str(workspace / ".ai-first" / "audit.db"))

    workflow_engine = WorkflowEngine(
        runtime_engine=runtime_engine,
        execution_context=context,
        persistence=persistence,
        pack_registry=pack_registry,
        governance_hooks=None,
    )

    with _bridge_silence(True):
        workflow_engine.resume_workflow(
            workflow_id=workflow_execution_id,
            decision=decision,
            approver=approver,
        )

    _emit_workflow_record(
        record_id=record_id,
        execution_id=execution_id,
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        quest_id=quest_id,
        user_id=user_id,
        persistence=persistence,
        workflow_execution_id=workflow_execution_id,
        schema=schema,
        start_iso=start_iso,
    )


@bridge_group.command("workflow-cancel")
@click.option("--execution-id", required=True)
@click.option("--trace-id", required=True)
@click.option("--parent-trace-id")
@click.option("--quest-id")
@click.option("--user-id", required=True)
@click.option("--workflow-execution-id", required=True)
@click.option("--reason", default="Cancelled")
@click.option("--rollback", is_flag=True, default=False)
@click.option(
    "--schema-path",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=None,
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
)
def bridge_workflow_cancel(
    execution_id: str,
    trace_id: str,
    parent_trace_id: Optional[str],
    quest_id: Optional[str],
    user_id: str,
    workflow_execution_id: str,
    reason: str,
    rollback: bool,
    schema_path: Optional[Path],
    workspace: Path,
):
    workspace.mkdir(parents=True, exist_ok=True)

    record_id = uuid.uuid4().hex
    start_iso = _now_iso()

    schema_from_env = os.getenv("AEGIS_WORKFLOW_RECORD_SCHEMA")
    effective_schema_path = schema_path
    if effective_schema_path is None and schema_from_env:
        effective_schema_path = Path(schema_from_env)
    schema: Optional[Dict[str, Any]] = None
    if effective_schema_path is not None:
        schema = _load_json_schema(effective_schema_path)

    with _bridge_silence(True):
        _, runtime_engine, _, pack_registry, _ = _build_facade_runtime(workspace, quiet=True)

    context = ExecutionContext(
        user_id=user_id,
        workspace_root=workspace,
        session_id=f"aegis_{trace_id}",
        confirmation_callback=lambda _prompt, _meta: True,
        undo_enabled=True,
    )
    context.metadata.update({"traceId": trace_id})
    if parent_trace_id:
        context.metadata.update({"parentTraceId": parent_trace_id})
    if quest_id:
        context.metadata.update({"questId": quest_id})

    persistence = WorkflowPersistence(str(workspace / ".ai-first" / "audit.db"))

    workflow_engine = WorkflowEngine(
        runtime_engine=runtime_engine,
        execution_context=context,
        persistence=persistence,
        pack_registry=pack_registry,
        governance_hooks=None,
    )

    with _bridge_silence(True):
        workflow_engine.cancel_workflow(
            workflow_id=workflow_execution_id,
            reason=reason,
            rollback=rollback,
        )

    _emit_workflow_record(
        record_id=record_id,
        execution_id=execution_id,
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        quest_id=quest_id,
        user_id=user_id,
        persistence=persistence,
        workflow_execution_id=workflow_execution_id,
        schema=schema,
        start_iso=start_iso,
    )


@bridge_group.command("workflow-rollback")
@click.option("--execution-id", required=True)
@click.option("--trace-id", required=True)
@click.option("--parent-trace-id")
@click.option("--quest-id")
@click.option("--user-id", required=True)
@click.option("--workflow-execution-id", required=True)
@click.option("--reason", default="Manual rollback")
@click.option(
    "--schema-path",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=None,
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
)
def bridge_workflow_rollback(
    execution_id: str,
    trace_id: str,
    parent_trace_id: Optional[str],
    quest_id: Optional[str],
    user_id: str,
    workflow_execution_id: str,
    reason: str,
    schema_path: Optional[Path],
    workspace: Path,
):
    workspace.mkdir(parents=True, exist_ok=True)

    record_id = uuid.uuid4().hex
    start_iso = _now_iso()

    schema_from_env = os.getenv("AEGIS_WORKFLOW_RECORD_SCHEMA")
    effective_schema_path = schema_path
    if effective_schema_path is None and schema_from_env:
        effective_schema_path = Path(schema_from_env)
    schema: Optional[Dict[str, Any]] = None
    if effective_schema_path is not None:
        schema = _load_json_schema(effective_schema_path)

    with _bridge_silence(True):
        _, runtime_engine, _, pack_registry, _ = _build_facade_runtime(workspace, quiet=True)

    context = ExecutionContext(
        user_id=user_id,
        workspace_root=workspace,
        session_id=f"aegis_{trace_id}",
        confirmation_callback=lambda _prompt, _meta: True,
        undo_enabled=True,
    )
    context.metadata.update({"traceId": trace_id})
    if parent_trace_id:
        context.metadata.update({"parentTraceId": parent_trace_id})
    if quest_id:
        context.metadata.update({"questId": quest_id})

    persistence = WorkflowPersistence(str(workspace / ".ai-first" / "audit.db"))

    workflow_engine = WorkflowEngine(
        runtime_engine=runtime_engine,
        execution_context=context,
        persistence=persistence,
        pack_registry=pack_registry,
        governance_hooks=None,
    )

    with _bridge_silence(True):
        workflow_engine.rollback_workflow(workflow_execution_id, reason=reason)

    _emit_workflow_record(
        record_id=record_id,
        execution_id=execution_id,
        trace_id=trace_id,
        parent_trace_id=parent_trace_id,
        quest_id=quest_id,
        user_id=user_id,
        persistence=persistence,
        workflow_execution_id=workflow_execution_id,
        schema=schema,
        start_iso=start_iso,
    )


@bridge_group.command("exec-workflow")
@click.option("--execution-id", required=True)
@click.option("--trace-id", required=True)
@click.option("--parent-trace-id")
@click.option("--quest-id")
@click.option("--user-id", required=True)
@click.option("--workflow-spec-json")
@click.option(
    "--workflow-spec-path",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=None,
)
@click.option(
    "--schema-path",
    type=click.Path(dir_okay=False, exists=True, path_type=Path),
    default=None,
    help="Optional JSON Schema file for validating the emitted JSON payload.",
)
@click.option(
    "--enable-governance-hooks",
    is_flag=True,
    default=False,
    help="Enable built-in governance hooks for pre_execution/pre_step/post_step/post_execution (for Aegis integration testing).",
)
@click.option(
    "--governance-decisions-json",
    default=None,
    help="Optional JSON object controlling governance decisions. Keys: 'pre_execution' (ALLOW/DENY/PAUSE), and 'pre_step' mapping stepName -> decision.",
)
@click.option(
    "--governance-hook-url",
    default=None,
    envvar="AEGIS_GOVERNANCE_HOOK_URL",
    help="Optional HTTP endpoint for real governance hooks. When set, the bridge will POST hook events to this URL.",
)
@click.option(
    "--governance-hook-timeout-ms",
    type=int,
    default=2000,
    envvar="AEGIS_GOVERNANCE_HOOK_TIMEOUT_MS",
    help="HTTP governance hook timeout in milliseconds.",
)
@click.option(
    "--governance-hook-fail-mode",
    type=str,
    default="DENY",
    envvar="AEGIS_GOVERNANCE_HOOK_FAIL_MODE",
    help="Decision to apply when hook call fails or times out: ALLOW | DENY | PAUSE.",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
)
def bridge_exec_workflow(
    execution_id: str,
    trace_id: str,
    parent_trace_id: Optional[str],
    quest_id: Optional[str],
    user_id: str,
    workflow_spec_json: Optional[str],
    workflow_spec_path: Optional[Path],
    schema_path: Optional[Path],
    enable_governance_hooks: bool,
    governance_decisions_json: Optional[str],
    governance_hook_url: Optional[str],
    governance_hook_timeout_ms: int,
    governance_hook_fail_mode: str,
    workspace: Path,
):
    if not workflow_spec_json and workflow_spec_path is None:
        _fail("Must provide either --workflow-spec-json or --workflow-spec-path", code=2)
    if workflow_spec_json and workflow_spec_path is not None:
        _fail("Provide only one of --workflow-spec-json or --workflow-spec-path", code=2)

    workspace.mkdir(parents=True, exist_ok=True)

    record_id = uuid.uuid4().hex
    start_iso = _now_iso()

    schema_from_env = os.getenv("AEGIS_WORKFLOW_RECORD_SCHEMA")
    effective_schema_path = schema_path
    if effective_schema_path is None and schema_from_env:
        effective_schema_path = Path(schema_from_env)
    schema: Optional[Dict[str, Any]] = None
    if effective_schema_path is not None:
        schema = _load_json_schema(effective_schema_path)

    if workflow_spec_json:
        raw_spec = _parse_json_arg(workflow_spec_json, name="--workflow-spec-json")
        if not isinstance(raw_spec, dict):
            _fail("--workflow-spec-json must be a JSON object", code=2)
        try:
            spec = WorkflowSpec.model_validate(raw_spec)
        except Exception as e:
            _fail(f"Workflow spec validation failed: {e}", code=2)
    else:
        spec = _load_workflow_spec_from_path(workflow_spec_path)  # type: ignore[arg-type]

    with _bridge_silence(True):
        _, runtime_engine, _, pack_registry, _ = _build_facade_runtime(workspace, quiet=True)

    context = ExecutionContext(
        user_id=user_id,
        workspace_root=workspace,
        session_id=f"aegis_{trace_id}",
        confirmation_callback=lambda _prompt, _meta: True,
        undo_enabled=True,
    )
    context.metadata.update({"traceId": trace_id})
    if parent_trace_id:
        context.metadata.update({"parentTraceId": parent_trace_id})
    if quest_id:
        context.metadata.update({"questId": quest_id})

    persistence = WorkflowPersistence(str(workspace / ".ai-first" / "audit.db"))

    decisions_from_env = os.getenv("AEGIS_GOVERNANCE_DECISIONS_JSON")
    decisions_payload = _parse_json_arg(
        governance_decisions_json or decisions_from_env,
        name="--governance-decisions-json/AEGIS_GOVERNANCE_DECISIONS_JSON",
    )
    if decisions_payload is None:
        decisions_payload = {}
    if decisions_payload is not None and not isinstance(decisions_payload, dict):
        _fail("Governance decisions must be a JSON object", code=2)

    if enable_governance_hooks and governance_hook_url:
        _fail(
            "Provide only one governance mode: either --enable-governance-hooks (built-in decisions) or --governance-hook-url (HTTP hooks)",
            code=2,
        )

    def _coerce_decision(value: Any) -> GovernanceDecision:
        if isinstance(value, GovernanceDecision):
            return value
        if value is None:
            return GovernanceDecision.ALLOW
        text = str(value).upper().strip()
        if text == "DENY":
            return GovernanceDecision.DENY
        if text in {"PAUSE", "PAUSED"}:
            return GovernanceDecision.PAUSE
        return GovernanceDecision.ALLOW

    governance_hooks = None
    if enable_governance_hooks:
        pre_exec_value = (decisions_payload or {}).get("pre_execution")
        pre_step_map = (decisions_payload or {}).get("pre_step") or {}
        if not isinstance(pre_step_map, dict):
            _fail("governance 'pre_step' must be a JSON object mapping stepName -> decision", code=2)

        def _pre_execution_hook(**kwargs):
            return _coerce_decision(pre_exec_value)

        def _pre_step_hook(step=None, **kwargs):
            step_name = getattr(step, "name", None)
            return _coerce_decision(pre_step_map.get(step_name))

        def _post_step_hook(**kwargs):
            return None

        def _post_execution_hook(**kwargs):
            return None

        governance_hooks = {
            "pre_execution": _pre_execution_hook,
            "pre_step": _pre_step_hook,
            "post_step": _post_step_hook,
            "post_execution": _post_execution_hook,
        }

    if governance_hook_url:
        governance_hooks = build_http_governance_hooks(
            GovernanceHttpConfig(
                hook_url=governance_hook_url,
                timeout_ms=governance_hook_timeout_ms,
                fail_mode=governance_hook_fail_mode,
            )
        )

    workflow_engine = WorkflowEngine(
        runtime_engine=runtime_engine,
        execution_context=context,
        persistence=persistence,
        pack_registry=pack_registry,
        governance_hooks=governance_hooks,
    )

    try:
        with _bridge_silence(True):
            workflow_execution_id = workflow_engine.submit_workflow(spec)
            workflow_engine.start_workflow(workflow_execution_id)

        _emit_workflow_record(
            record_id=record_id,
            execution_id=execution_id,
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            quest_id=quest_id,
            user_id=user_id,
            persistence=persistence,
            workflow_execution_id=workflow_execution_id,
            schema=schema,
            start_iso=start_iso,
        )
    except SystemExit:
        raise
    except BaseException as e:
        end_iso = _now_iso()
        category = _map_failure_category(e)
        payload = {
            "id": record_id,
            "executionId": execution_id,
            "traceId": trace_id,
            "parentTraceId": parent_trace_id,
            "questId": quest_id,
            "workflowExecutionId": None,
            "workflowName": getattr(spec, "name", None),
            "status": "failure" if category != "TIMEOUT" else "timeout",
            "error": {
                "category": category,
                "message": str(e),
                "details": None,
                "recoverable": False,
                "retryable": False,
            },
            "startTime": start_iso,
            "endTime": end_iso,
            "workflow": None,
            "steps": [],
            "userId": user_id,
            "metadata": None,
        }
        _print_json(payload)
        raise SystemExit(_map_exit_code(category))


@governance_group.group("facade")
def governance_facade_group():
    pass


@governance_facade_group.command("activate")
@click.argument("facade_name")
@click.option("--version", default=None, help="Facade version (default: latest)")
@click.option("--changed-by", default="cli_governance", help="Actor performing the change")
@click.option("--reason", required=True, help="Reason for state transition")
@click.option("--approval-id", default=None, help="Approval record id (optional)")
def governance_facade_activate(
    facade_name: str,
    version: Optional[str],
    changed_by: str,
    reason: str,
    approval_id: Optional[str],
):
    reg = SkillFacadeRegistry()
    load_facades_from_directory(reg, resolve_facades_dir(), activate=False, registered_by="cli")
    rec = reg.get_facade_record(facade_name, version=version)
    if rec is None:
        _fail(f"Facade not found: {facade_name}", code=4)
    reg.activate_facade(
        name=rec["name"],
        version=rec["version"],
        changed_by=changed_by,
        reason=reason,
        approval_id=approval_id,
    )
    console.print(f"[green]Facade activated[/green]: {rec['name']}@{rec['version']}")


@governance_facade_group.command("freeze")
@click.argument("facade_name")
@click.option("--version", default=None, help="Facade version (default: latest)")
@click.option("--changed-by", default="cli_governance", help="Actor performing the change")
@click.option("--reason", required=True, help="Reason for state transition")
@click.option("--approval-id", default=None, help="Approval record id (optional)")
def governance_facade_freeze(
    facade_name: str,
    version: Optional[str],
    changed_by: str,
    reason: str,
    approval_id: Optional[str],
):
    reg = SkillFacadeRegistry()
    load_facades_from_directory(reg, resolve_facades_dir(), activate=False, registered_by="cli")
    rec = reg.get_facade_record(facade_name, version=version)
    if rec is None:
        _fail(f"Facade not found: {facade_name}", code=4)
    reg.freeze_facade(
        name=rec["name"],
        version=rec["version"],
        changed_by=changed_by,
        reason=reason,
        approval_id=approval_id,
    )
    console.print(f"[yellow]Facade frozen[/yellow]: {rec['name']}@{rec['version']}")


@governance_facade_group.command("deprecate")
@click.argument("facade_name")
@click.option("--version", default=None, help="Facade version (default: latest)")
@click.option("--changed-by", default="cli_governance", help="Actor performing the change")
@click.option("--reason", required=True, help="Reason for state transition")
@click.option("--approval-id", default=None, help="Approval record id (optional)")
def governance_facade_deprecate(
    facade_name: str,
    version: Optional[str],
    changed_by: str,
    reason: str,
    approval_id: Optional[str],
):
    reg = SkillFacadeRegistry()
    load_facades_from_directory(reg, resolve_facades_dir(), activate=False, registered_by="cli")
    rec = reg.get_facade_record(facade_name, version=version)
    if rec is None:
        _fail(f"Facade not found: {facade_name}", code=4)
    reg.deprecate_facade(
        name=rec["name"],
        version=rec["version"],
        changed_by=changed_by,
        reason=reason,
        approval_id=approval_id,
    )
    console.print(f"[red]Facade deprecated[/red]: {rec['name']}@{rec['version']}")


@governance_group.group("pack")
def governance_pack_group():
    pass


def _pack_registry() -> PackRegistry:
    # Use a temp registry DB under the project workspace so repeated CLI invocations
    # during tests do not pollute ~/.ai-first/pack_registry.db.
    workspace_db = Path.cwd() / ".ai-first" / "pack_registry.db"
    workspace_db.parent.mkdir(parents=True, exist_ok=True)
    reg = PackRegistry(db_path=workspace_db, capability_registry=None)
    load_packs_from_directory(reg, resolve_packs_dir(), activate=True, registered_by="cli")
    return reg


@governance_pack_group.command("activate")
@click.argument("pack_ref")
@click.option("--version", default=None, help="Pack version (default: latest)")
@click.option("--changed-by", default="cli_governance", help="Actor performing the change")
@click.option("--reason", required=True, help="Reason for state transition")
@click.option("--approval-id", default=None, help="Approval record id (optional)")
def governance_pack_activate(
    pack_ref: str,
    version: Optional[str],
    changed_by: str,
    reason: str,
    approval_id: Optional[str],
):
    reg = _pack_registry()
    rec = reg.get_pack_record(pack_ref=pack_ref, version=version)
    if rec is None:
        _fail(f"Pack not found: {pack_ref}", code=4)
    from specs.capability_pack import PackState
    reg.transition_state(
        pack_id=rec["pack_id"],
        version=rec["pack_version"],
        new_state=PackState.ACTIVE,
        changed_by=changed_by,
        reason=reason,
        approval_id=approval_id,
    )
    console.print(f"[green]Pack activated[/green]: {rec['pack_id']}@{rec['pack_version']}")


@governance_pack_group.command("freeze")
@click.argument("pack_ref")
@click.option("--version", default=None, help="Pack version (default: latest)")
@click.option("--changed-by", default="cli_governance", help="Actor performing the change")
@click.option("--reason", required=True, help="Reason for state transition")
@click.option("--approval-id", default=None, help="Approval record id (optional)")
def governance_pack_freeze(
    pack_ref: str,
    version: Optional[str],
    changed_by: str,
    reason: str,
    approval_id: Optional[str],
):
    reg = _pack_registry()
    rec = reg.get_pack_record(pack_ref=pack_ref, version=version)
    if rec is None:
        _fail(f"Pack not found: {pack_ref}", code=4)
    from specs.capability_pack import PackState

    reg.transition_state(
        pack_id=rec["pack_id"],
        version=rec["pack_version"],
        new_state=PackState.FROZEN,
        changed_by=changed_by,
        reason=reason,
        approval_id=approval_id,
    )
    console.print(f"[yellow]Pack frozen[/yellow]: {rec['pack_id']}@{rec['pack_version']}")


@governance_pack_group.command("deprecate")
@click.argument("pack_ref")
@click.option("--version", default=None, help="Pack version (default: latest)")
@click.option("--changed-by", default="cli_governance", help="Actor performing the change")
@click.option("--reason", required=True, help="Reason for state transition")
@click.option("--approval-id", default=None, help="Approval record id (optional)")
def governance_pack_deprecate(
    pack_ref: str,
    version: Optional[str],
    changed_by: str,
    reason: str,
    approval_id: Optional[str],
):
    reg = _pack_registry()
    rec = reg.get_pack_record(pack_ref=pack_ref, version=version)
    if rec is None:
        _fail(f"Pack not found: {pack_ref}", code=4)
    from specs.capability_pack import PackState

    reg.transition_state(
        pack_id=rec["pack_id"],
        version=rec["pack_version"],
        new_state=PackState.DEPRECATED,
        changed_by=changed_by,
        reason=reason,
        approval_id=approval_id,
    )
    console.print(f"[red]Pack deprecated[/red]: {rec['pack_id']}@{rec['pack_version']}")


@cli.group("facade")
def facade_group():
    pass


@cli.group("sidecar")
def sidecar_group():
    pass


@sidecar_group.group("dev-browser")
def sidecar_dev_browser_group():
    pass


@sidecar_dev_browser_group.command("start")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", type=int, default=8787, show_default=True)
@click.option(
    "--allowed-domain",
    "allowed_domains",
    multiple=True,
)
@click.option("--timeout-seconds", type=float, default=20.0, show_default=True)
@click.option("--background", is_flag=True)
@click.option("--json", "json_output", is_flag=True)
def sidecar_dev_browser_start(
    host: str,
    port: int,
    allowed_domains: Tuple[str, ...],
    timeout_seconds: float,
    background: bool,
    json_output: bool,
):
    import runtime.sidecars

    sidecar_path = Path(runtime.sidecars.__file__).resolve().parent / "dev_browser_sidecar.py"
    if not sidecar_path.exists():
        if json_output:
            _fail_json(
                {
                    "error": {
                        "type": "sidecar_not_found",
                        "message": "dev-browser sidecar entry not found",
                    }
                },
                code=4,
            )
        _fail("dev-browser sidecar entry not found", code=4)

    env = os.environ.copy()
    if allowed_domains:
        env["DEV_BROWSER_ALLOWED_DOMAINS"] = ",".join([d for d in allowed_domains if d])
    env["DEV_BROWSER_TIMEOUT_SECONDS"] = str(timeout_seconds)

    cmd = [sys.executable, str(sidecar_path), "--host", host, "--port", str(port)]
    if background:
        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        payload = {
            "status": "started",
            "sidecar": "dev-browser",
            "pid": proc.pid,
            "host": host,
            "port": port,
        }
        if json_output:
            _print_json(payload)
            return
        console.print(payload)
        return

    if json_output:
        _print_json({"status": "running", "sidecar": "dev-browser", "host": host, "port": port})
    subprocess.run(cmd, env=env, check=True)


@facade_group.command("run")
@click.argument("facade_name")
@click.option("--workflow", "workflow_name", required=True, help="Workflow to execute")
@click.option("--json", "json_output", is_flag=True)
@click.option(
    "--input",
    "inputs",
    multiple=True,
    help="Workflow initial_state override in key=value form. Repeatable.",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
    help="Workspace directory for operations",
)
def facade_run(
    facade_name: str,
    workflow_name: str,
    json_output: bool,
    inputs: Tuple[str, ...],
    workspace: Path,
):
    workspace.mkdir(parents=True, exist_ok=True)

    _, runtime_engine, facade_registry, pack_registry, audit_logger = _build_facade_runtime(workspace)

    rec = facade_registry.get_facade_record(facade_name)
    if rec is None:
        if json_output:
            _fail_json(
                {
                    "error": {"type": "facade_not_found", "message": f"Facade not found: {facade_name}"},
                    "facade": {"name": facade_name},
                },
                code=4,
            )
        _fail(f"Facade not found: {facade_name}", code=4)
    if rec["state"].value != "ACTIVE":
        if json_output:
            _fail_json(
                {
                    "error": {
                        "type": "facade_not_active",
                        "message": f"Facade is not ACTIVE: {facade_name} ({rec['state'].value})",
                    },
                    "facade": {"name": facade_name, "state": rec["state"].value},
                },
                code=4,
            )
        _fail(f"Facade is not ACTIVE: {facade_name} ({rec['state'].value})", code=4)

    facade = rec["spec"]

    allowed_workflows: List[str] = []
    for target in [facade.routes.primary, facade.routes.fallback]:
        if target is None:
            continue
        if target.type.value == "workflow":
            allowed_workflows.append(target.ref)
        elif target.type.value == "pack":
            pack = pack_registry.get_pack(target.ref)
            if pack is None:
                from specs.capability_pack import PackState

                for p in pack_registry.list_packs(state=PackState.ACTIVE, pack_name=target.ref):
                    pack = p
                    break
            if pack is not None:
                allowed_workflows.extend(pack.includes.workflows or [])

    allowed_workflows = sorted(set([w for w in allowed_workflows if w]))
    if workflow_name not in allowed_workflows:
        if json_output:
            _fail_json(
                {
                    "error": {
                        "type": "workflow_not_allowed",
                        "message": f"Workflow '{workflow_name}' is not allowed by facade '{facade_name}'.",
                    },
                    "facade": {"name": facade_name},
                    "requested_workflow": workflow_name,
                    "allowed_workflows": allowed_workflows,
                },
                code=4,
            )
        _fail(
            f"Workflow '{workflow_name}' is not allowed by facade '{facade_name}'. Allowed: {', '.join(allowed_workflows)}",
            code=4,
        )

    status = _print_route_status(
        facade_registry=facade_registry,
        pack_registry=pack_registry,
        facade_name=facade.name,
        route_type="workflow",
        ref=workflow_name,
        allowed_workflows=allowed_workflows,
        json_output=json_output,
    )

    pack = _find_pack_for_workflow(pack_registry, workflow_name)
    gate = _governance_gate_or_exit(pack)
    if gate is not None:
        if json_output:
            _fail_json({"status": "blocked", **status, **gate}, code=3)
        _fail(str(gate["error"]["message"]), code=3)

    input_dict = _parse_kv_inputs(inputs)
    spec = load_workflow_spec_by_id(workflow_name)
    spec.initial_state.update(input_dict)
    if getattr(spec, "metadata", None) is not None:
        spec.metadata.triggered_by = f"cli.facade:{facade_name}"

    context = ExecutionContext(
        user_id="cli_user",
        workspace_root=workspace,
        session_id=f"cli_{uuid.uuid4().hex}",
        confirmation_callback=confirmation_callback,
        undo_enabled=True,
    )

    workflow_engine = WorkflowEngine(
        runtime_engine=runtime_engine,
        execution_context=context,
        persistence=WorkflowPersistence(str(workspace / ".ai-first" / "audit.db")),
        pack_registry=pack_registry,
    )

    workflow_id = workflow_engine.submit_workflow(spec)
    workflow_engine.start_workflow(workflow_id)

    audit_logger.log_action(
        session_id=context.session_id,
        user_id=context.user_id,
        capability_id=f"facade:{facade.name}",
        action_type="start_workflow",
        params={"facade": facade_name, "workflow": workflow_name, "input": input_dict},
        result={"workflow_id": workflow_id},
        status="success",
    )
    if json_output:
        _print_json({"status": "workflow_started", **status, "workflow_id": workflow_id})
        return
    console.print(f"[green]Started workflow[/green]: {workflow_id}")

@cli.command()
@click.option(
    "--specs-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing capability YAML specs",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
    help="Workspace directory for operations",
)
def init(specs_dir: Path, workspace: Path):
    """Initialize runtime and load capabilities"""
    console.print(Panel.fit(
        "🚀 AI-First Runtime Initialization",
        border_style="blue"
    ))
    
    # Create workspace
    workspace.mkdir(parents=True, exist_ok=True)
    console.print(f"✅ Workspace: {workspace}")
    
    # Create registry and load stdlib
    registry = CapabilityRegistry()
    loaded = load_stdlib(registry, specs_dir)
    
    if loaded == 0:
        console.print("❌ No capabilities loaded!", style="bold red")
        sys.exit(1)
    
    # Show summary
    info = get_stdlib_info()
    console.print(f"\n✅ Initialized with {info['total_capabilities']} capabilities")
    console.print(f"📦 Namespaces: {', '.join(info['namespaces'].keys())}")


@cli.command()
@click.option(
    "--specs-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing capability YAML specs",
)
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
    help="Workspace directory for operations",
)
@click.argument("capability_id")
@click.option(
    "--params",
    type=str,
    required=True,
    help="JSON string of parameters",
)
@click.option(
    "--no-confirm",
    is_flag=True,
    help="Skip confirmation prompts (dangerous!)",
)
def execute(
    specs_dir: Path,
    workspace: Path,
    capability_id: str,
    params: str,
    no_confirm: bool,
):
    _forbidden("CLI direct capability execution is prohibited in v3.1. Use 'airun nl' or 'airun facade run'.")


@cli.command()
@click.option(
    "--specs-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing capability YAML specs",
)
@click.option(
    "--namespace",
    type=str,
    help="Filter by namespace (e.g., io.fs)",
)
def list_capabilities(specs_dir: Path, namespace: Optional[str]):
    _forbidden("CLI direct capability inspection is prohibited in v3.1. Use Facade surfaces.")


@cli.command()
@click.option(
    "--specs-dir",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
    help="Directory containing capability YAML specs",
)
@click.argument("capability_id")
def inspect(specs_dir: Path, capability_id: str):
    _forbidden("CLI direct capability inspection is prohibited in v3.1. Use Facade surfaces.")


@cli.command()
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
    help="Workspace directory",
)
@click.option(
    "--steps",
    type=int,
    default=1,
    help="Number of operations to undo",
)
def undo(workspace: Path, steps: int):
    """Undo last N operations"""
    
    undo_manager = UndoManager(workspace / ".ai-first" / "backups")
    
    if undo_manager.is_empty():
        console.print("ℹ️  No operations to undo", style="yellow")
        return
    
    try:
        undone = undo_manager.rollback(steps)
        
        console.print(f"✅ Undone {len(undone)} operation(s):", style="bold green")
        for desc in undone:
            console.print(f"  ↩️  {desc}")
    
    except Exception as e:
        console.print(f"❌ Undo failed: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option(
    "--workspace",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path.cwd() / "workspace",
    help="Workspace directory",
)
@click.option(
    "--count",
    type=int,
    default=10,
    help="Number of recent operations to show",
)
def history(workspace: Path, count: int):
    """View undo history"""
    
    undo_manager = UndoManager(workspace / ".ai-first" / "backups")
    
    if undo_manager.is_empty():
        console.print("ℹ️  No operations in history", style="yellow")
        return
    
    recent = undo_manager.peek(count)
    
    # Create table
    table = Table(title=f"📜 Recent Operations ({len(recent)})")
    table.add_column("#", style="cyan")
    table.add_column("Capability", style="white")
    table.add_column("Description", style="yellow")
    table.add_column("Timestamp", style="green")
    
    for i, op in enumerate(reversed(recent), 1):
        table.add_row(
            str(i),
            op["capability_id"],
            op["description"],
            op["timestamp"],
        )
    
    console.print(table)


def main():
    """Entry point for CLI"""
    cli()


if __name__ == "__main__":
    main()

@cli.command()
def dashboard():
    """
    Launch the interactive TUI dashboard.
    
    Monitor and control workflows in real-time with a terminal UI.
    """
    try:
        from .dashboard import run_dashboard
        run_dashboard()
    except ImportError as e:
        console.print("[red]Error: Textual not installed. Install with: pip install textual[/red]")
        console.print(f"[dim]{e}[/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Dashboard error: {e}[/red]")
        sys.exit(1)


@cli.group()
def workflow():
    """
    Workflow management commands.
    
    Submit, start, pause, resume, and rollback workflows.
    """
    pass


@workflow.command("list")
def workflow_list():
    """List all workflows."""
    import sqlite3
    from rich.table import Table
    
    try:
        conn = sqlite3.connect("audit.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT workflow_id, name, status, owner, started_at
            FROM workflows
            ORDER BY started_at DESC
            LIMIT 20
        """)
        
        table = Table(title="Workflows")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Owner", style="blue")
        table.add_column("Started", style="magenta")
        
        for row in cursor.fetchall():
            workflow_id, name, status, owner, started_at = row
            table.add_row(
                workflow_id[:8],
                name,
                status,
                owner,
                started_at or "N/A"
            )
        
        console.print(table)
        conn.close()
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@workflow.command("resume")
@click.argument("workflow_id")
@click.option("--decision", type=click.Choice(["approve", "reject"]), required=True, help="Approval decision")
@click.option("--approver", default="cli_user", help="Name of approver")
def workflow_resume(workflow_id: str, decision: str, approver: str):
    """
    Resume a PAUSED workflow with approval decision.
    
    WORKFLOW_ID: The workflow identifier (full or prefix)
    """
    try:
        # Import workflow engine
        from runtime.workflow.engine import WorkflowEngine
        from runtime.workflow.persistence import WorkflowPersistence
        from runtime.workflow.human_approval import HumanApprovalManager
        
        # Initialize engine
        persistence = WorkflowPersistence()
        approval_manager = HumanApprovalManager()
        engine = WorkflowEngine(
            persistence=persistence,
            approval_manager=approval_manager
        )
        
        # Find workflow by prefix
        import sqlite3
        conn = sqlite3.connect("audit.db")
        cursor = conn.cursor()
        cursor.execute("SELECT workflow_id FROM workflows WHERE workflow_id LIKE ?", (f"{workflow_id}%",))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            console.print(f"[red]Workflow not found: {workflow_id}[/red]")
            sys.exit(1)
        
        full_workflow_id = result[0]
        
        # Resume workflow
        console.print(f"[yellow]Resuming workflow {full_workflow_id} with decision: {decision}[/yellow]")
        engine.resume_workflow(full_workflow_id, decision, approver)
        
        console.print(f"[green]✓ Workflow {decision}d successfully[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)
