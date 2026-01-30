#!/usr/bin/env python3

import argparse
import contextlib
import io
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    import yaml  # noqa: F401
except ModuleNotFoundError as e:
    exe = sys.executable
    raise SystemExit(
        "Missing dependency 'pyyaml' for this interpreter. "
        f"Current python: {exe}. "
        "Install deps for the same interpreter, e.g. 'python -m pip install -e .' "
        "or run this script with the interpreter where deps are installed."
    ) from e

from runtime.audit import AuditLogger
from runtime.engine import RuntimeEngine
from runtime.registry import CapabilityRegistry
from runtime.stdlib.loader import STDLIB_HANDLERS
from runtime.types import ExecutionContext
from runtime.undo.manager import UndoManager
from runtime.workflow.engine import WorkflowEngine, WorkflowStatus
from runtime.workflow.persistence import WorkflowPersistence
from runtime.workflow.spec_loader import load_workflow_spec_by_id


@dataclass(frozen=True)
class RunResult:
    ok: bool
    duration_ms: float
    error: Optional[str] = None


def _load_stdlib_subset(*, registry: CapabilityRegistry, specs_dir: Path, capability_ids: List[str]) -> None:
    missing = [cid for cid in capability_ids if cid not in STDLIB_HANDLERS]
    if missing:
        raise RuntimeError(f"Missing stdlib handler(s): {missing}")

    for capability_id in capability_ids:
        handler_class = STDLIB_HANDLERS[capability_id]

        spec_filename = capability_id.replace(".", "_") + ".yaml"
        spec_path = specs_dir / spec_filename
        if not spec_path.exists():
            raise FileNotFoundError(f"Stdlib spec not found: {spec_path}")

        with open(spec_path, "r", encoding="utf-8") as f:
            spec_dict = yaml.safe_load(f)

        if spec_dict["meta"]["id"] != capability_id:
            raise ValueError(
                f"Stdlib spec ID mismatch: {spec_path} declares {spec_dict['meta']['id']}, expected {capability_id}"
            )

        handler = handler_class(spec_dict)
        registry.register(capability_id, handler, spec_dict)


def _run_one(*, workflow_spec_id: str, work_root: Path, i: int, verbose: bool) -> RunResult:
    run_id = uuid.uuid4().hex
    workspace = work_root / f"w{i:04d}_{run_id}"
    workspace.mkdir(parents=True, exist_ok=True)

    null_out: contextlib.AbstractContextManager
    if verbose:
        null_out = contextlib.nullcontext()
    else:
        null_out = contextlib.ExitStack()
        stack = null_out
        stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        stack.enter_context(contextlib.redirect_stderr(io.StringIO()))

    with null_out:
        specs_dir = REPO_ROOT / "capabilities" / "validated" / "stdlib"
        registry = CapabilityRegistry()

        # Minimal stdlib-only load to avoid noisy governance-denied registrations
        _load_stdlib_subset(
            registry=registry,
            specs_dir=specs_dir,
            capability_ids=[
                "sys.info.get_time",
                "text.template.render",
                "io.fs.write_file",
                "io.fs.hash_file",
            ],
        )

        backup_dir = workspace / ".ai-first" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        undo_manager = UndoManager(backup_dir)

        audit_db_path = workspace / ".ai-first" / "audit.db"
        audit_db_path.parent.mkdir(parents=True, exist_ok=True)
        audit_logger = AuditLogger(str(audit_db_path))

        runtime_engine = RuntimeEngine(registry, undo_manager=undo_manager, audit_logger=audit_logger)

        context = ExecutionContext(
            user_id="load_test",
            workspace_root=workspace,
            session_id=f"load_{run_id}",
            confirmation_callback=lambda _msg, _details: True,
            undo_enabled=True,
        )

        spec = load_workflow_spec_by_id(workflow_spec_id)
        spec.initial_state["run_id"] = run_id

        engine = WorkflowEngine(
            runtime_engine=runtime_engine,
            execution_context=context,
            persistence=WorkflowPersistence(str(audit_db_path)),
            pack_registry=None,
        )

        started = time.perf_counter()
        try:
            workflow_id = engine.submit_workflow(spec)
            engine.start_workflow(workflow_id)

            wf_ctx = engine.workflows[workflow_id]
            if wf_ctx.spec.metadata.status == WorkflowStatus.PAUSED:
                engine.resume_workflow(workflow_id, decision="approve", approver=context.user_id)

            wf_ctx = engine.workflows[workflow_id]
            ok = wf_ctx.spec.metadata.status == WorkflowStatus.COMPLETED
            dur_ms = (time.perf_counter() - started) * 1000
            if not ok:
                return RunResult(ok=False, duration_ms=dur_ms, error=str(wf_ctx.spec.metadata.status.value))
            return RunResult(ok=True, duration_ms=dur_ms)
        except Exception as e:
            dur_ms = (time.perf_counter() - started) * 1000
            return RunResult(ok=False, duration_ms=dur_ms, error=f"{type(e).__name__}: {e}")
        finally:
            try:
                audit_logger.shutdown()
            except Exception:
                pass


def main() -> None:
    p = argparse.ArgumentParser(description="Load test workflows with concurrency")
    p.add_argument("--workflow", default="load_test_quick", help="workflow_id to run")
    p.add_argument("--concurrency", type=int, default=100)
    p.add_argument("--total", type=int, default=200)
    p.add_argument("--workdir", default=str(Path.cwd() / "workspace" / "load_test"))
    p.add_argument("--verbose", action="store_true", help="show per-worker logs")
    args = p.parse_args()

    work_root = Path(args.workdir)
    work_root.mkdir(parents=True, exist_ok=True)

    total = int(args.total)
    concurrency = max(1, int(args.concurrency))

    started = time.perf_counter()
    results: List[RunResult] = []

    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [
            ex.submit(_run_one, workflow_spec_id=args.workflow, work_root=work_root, i=i, verbose=bool(args.verbose))
            for i in range(total)
        ]
        for fut in as_completed(futures):
            results.append(fut.result())

    elapsed_s = time.perf_counter() - started

    ok = [r for r in results if r.ok]
    fail = [r for r in results if not r.ok]

    durations = [r.duration_ms for r in ok]
    durations.sort()

    def _pct(pct: float) -> float:
        if not durations:
            return 0.0
        k = int(round((pct / 100.0) * (len(durations) - 1)))
        return float(durations[max(0, min(len(durations) - 1, k))])

    summary: Dict[str, Any] = {
        "workflow": args.workflow,
        "total": total,
        "concurrency": concurrency,
        "ok": len(ok),
        "failed": len(fail),
        "elapsed_s": elapsed_s,
        "throughput_wf_per_s": (len(ok) / elapsed_s) if elapsed_s > 0 else 0.0,
        "latency_ms": {
            "min": float(min(durations)) if durations else 0.0,
            "p50": _pct(50),
            "p95": _pct(95),
            "p99": _pct(99),
            "max": float(max(durations)) if durations else 0.0,
            "mean": float(statistics.mean(durations)) if durations else 0.0,
        },
        "errors": {},
        "workdir": str(work_root),
    }

    errors: Dict[str, int] = {}
    for r in fail:
        key = r.error or "unknown"
        errors[key] = errors.get(key, 0) + 1
    summary["errors"] = dict(sorted(errors.items(), key=lambda kv: (-kv[1], kv[0])))

    import json

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
