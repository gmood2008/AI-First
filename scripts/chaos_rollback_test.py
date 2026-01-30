#!/usr/bin/env python3

import argparse
import contextlib
import io
import random
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

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
        "Install deps for the same interpreter, e.g. 'python -m pip install -e .'"
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
class ChaosResult:
    ok: bool
    rolled_back: bool
    duration_ms: float
    file_removed: bool
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


class ChaosRuntimeEngine(RuntimeEngine):
    def __init__(
        self,
        *,
        registry: CapabilityRegistry,
        undo_manager: UndoManager,
        audit_logger: AuditLogger,
        fail_on_capability_id: Optional[str],
        fail_probability: float,
        seed: int,
    ):
        super().__init__(registry, undo_manager=undo_manager, audit_logger=audit_logger)
        self._fail_on_capability_id = fail_on_capability_id
        self._fail_probability = fail_probability
        self._rnd = random.Random(seed)

    def execute(self, capability_id: str, params: Dict, context: ExecutionContext):
        if self._fail_on_capability_id and capability_id == self._fail_on_capability_id:
            if self._rnd.random() < self._fail_probability:
                # Mark injection on the execution context. WorkflowEngine converts execution
                # exceptions into FAILED->ROLLED_BACK and does not propagate, so we need an
                # explicit signal for accurate metrics.
                try:
                    setattr(context, "_chaos_injected", True)
                except Exception:
                    pass
                raise RuntimeError(f"CHAOS_INJECTED_FAILURE: {capability_id}")
        return super().execute(capability_id, params, context)


def _run_one(
    *,
    workflow_spec_id: str,
    work_root: Path,
    i: int,
    fail_on: str,
    fail_probability: float,
    verbose: bool,
    seed: int,
) -> ChaosResult:
    run_id = uuid.uuid4().hex
    workspace = work_root / f"c{i:04d}_{run_id}"
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

        runtime_engine = ChaosRuntimeEngine(
            registry=registry,
            undo_manager=undo_manager,
            audit_logger=audit_logger,
            fail_on_capability_id=fail_on,
            fail_probability=fail_probability,
            seed=seed ^ i,
        )

        context = ExecutionContext(
            user_id="chaos_test",
            workspace_root=workspace,
            session_id=f"chaos_{run_id}",
            confirmation_callback=lambda _msg, _details: True,
            undo_enabled=True,
        )

        # For metrics
        try:
            setattr(context, "_chaos_injected", False)
        except Exception:
            pass

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
            status = wf_ctx.spec.metadata.status

            injected = bool(getattr(context, "_chaos_injected", False))

            out_path = workspace / "out.txt"
            file_removed = not out_path.exists()

            dur_ms = (time.perf_counter() - started) * 1000
            return ChaosResult(
                ok=True,
                rolled_back=status == WorkflowStatus.ROLLED_BACK,
                duration_ms=dur_ms,
                file_removed=file_removed,
                error="CHAOS_INJECTED" if injected else None,
            )
        except Exception as e:
            dur_ms = (time.perf_counter() - started) * 1000
            out_path = workspace / "out.txt"
            file_removed = not out_path.exists()
            return ChaosResult(
                ok=False,
                rolled_back=False,
                duration_ms=dur_ms,
                file_removed=file_removed,
                error=f"{type(e).__name__}: {e}",
            )
        finally:
            try:
                audit_logger.shutdown()
            except Exception:
                pass


def main() -> None:
    p = argparse.ArgumentParser(description="Chaos rollback verification")
    p.add_argument("--workflow", default="load_test_quick")
    p.add_argument("--concurrency", type=int, default=20)
    p.add_argument("--total", type=int, default=100)
    p.add_argument("--workdir", default=str(Path.cwd() / "workspace" / "chaos_test"))
    p.add_argument("--fail-on", default="io.fs.hash_file")
    p.add_argument("--fail-prob", type=float, default=0.5)
    p.add_argument("--seed", type=int, default=1337)
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    work_root = Path(args.workdir)
    work_root.mkdir(parents=True, exist_ok=True)

    total = int(args.total)
    concurrency = max(1, int(args.concurrency))

    results: List[ChaosResult] = []
    started = time.perf_counter()

    # In multi-threaded runs, per-thread redirection can still leak output.
    # We additionally silence stdout/stderr in the main thread unless verbose.
    with (
        contextlib.nullcontext()
        if args.verbose
        else contextlib.ExitStack()
    ) as _stack:
        if not args.verbose:
            assert isinstance(_stack, contextlib.ExitStack)
            _stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            _stack.enter_context(contextlib.redirect_stderr(io.StringIO()))

        with ThreadPoolExecutor(max_workers=concurrency) as ex:
            futures = [
                ex.submit(
                    _run_one,
                    workflow_spec_id=args.workflow,
                    work_root=work_root,
                    i=i,
                    fail_on=args.fail_on,
                    fail_probability=float(args.fail_prob),
                    verbose=bool(args.verbose),
                    seed=int(args.seed),
                )
                for i in range(total)
            ]
            for fut in as_completed(futures):
                results.append(fut.result())

    elapsed_s = time.perf_counter() - started

    injected = [r for r in results if r.error == "CHAOS_INJECTED"]
    rolled_back = [r for r in results if r.rolled_back]
    file_ok = [r for r in results if r.file_removed]

    summary = {
        "workflow": args.workflow,
        "total": total,
        "concurrency": concurrency,
        "fail_on": args.fail_on,
        "fail_prob": float(args.fail_prob),
        "elapsed_s": elapsed_s,
        "injected_failures": len(injected),
        "rolled_back": len(rolled_back),
        "file_removed": len(file_ok),
        "ok": len([r for r in results if r.ok]),
        "failed": len([r for r in results if not r.ok]),
        "workdir": str(work_root),
    }

    import json

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
