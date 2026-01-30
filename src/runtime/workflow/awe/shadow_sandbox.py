from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.types import ActionOutput, ExecutionContext, ExecutionResult, ExecutionStatus


@dataclass
class ShadowOp:
    capability_id: str
    params: Dict[str, Any]
    side_effects: List[str] = field(default_factory=list)


@dataclass
class ShadowReport:
    ops: List[ShadowOp] = field(default_factory=list)


class ShadowRuntimeEngine:
    def __init__(self, runtime_engine: Any):
        self._runtime_engine = runtime_engine
        self.registry = getattr(runtime_engine, "registry", None)
        self.report = ShadowReport()

    def execute(self, capability_id: str, params: Dict[str, Any], context: ExecutionContext) -> ExecutionResult:
        side_effects: List[str] = []
        try:
            if self.registry is not None:
                handler = self.registry.get_handler(capability_id)
                side_effects = handler.contracts.get("side_effects", []) if getattr(handler, "contracts", None) else []
        except Exception:
            side_effects = []

        self.report.ops.append(
            ShadowOp(capability_id=capability_id, params=params, side_effects=list(side_effects))
        )

        # dry-run: never call underlying runtime_engine.execute
        return ExecutionResult(
            capability_id=capability_id,
            status=ExecutionStatus.SUCCESS,
            outputs={
                "shadow": True,
                "capability_id": capability_id,
                "side_effects": side_effects,
            },
            execution_time_ms=0.0,
            undo_available=False,
            metadata={"mode": "shadow"},
        )


class ShadowSandbox:
    def __init__(self) -> None:
        self._engine: Optional[ShadowRuntimeEngine] = None

    def wrap_runtime_engine(self, runtime_engine: Any) -> ShadowRuntimeEngine:
        self._engine = ShadowRuntimeEngine(runtime_engine)
        return self._engine

    def get_report(self) -> ShadowReport:
        if self._engine is None:
            return ShadowReport()
        return self._engine.report

    @staticmethod
    def is_write_side_effect(side_effects: List[str]) -> bool:
        return any(
            s in {"filesystem_write", "network_write", "exec"} for s in (side_effects or [])
        )
