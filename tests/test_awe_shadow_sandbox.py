from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from runtime.types import ExecutionContext
from runtime.workflow.awe.shadow_sandbox import ShadowSandbox


@dataclass
class _FakeHandler:
    contracts: Dict[str, Any]


class _FakeRegistry:
    def __init__(self, side_effects: List[str]):
        self._handler = _FakeHandler(contracts={"side_effects": side_effects})

    def get_handler(self, capability_id: str) -> _FakeHandler:
        return self._handler


class _FakeRuntimeEngine:
    def __init__(self, side_effects: List[str]):
        self.registry = _FakeRegistry(side_effects)

    def execute(self, capability_id: str, params: Dict[str, Any], context: ExecutionContext):
        raise AssertionError("should not execute in shadow mode")


def test_shadow_sandbox_records_ops_without_side_effects(tmp_path: Path) -> None:
    ctx = ExecutionContext(user_id="u", workspace_root=tmp_path, session_id="s")
    sandbox = ShadowSandbox()
    shadow_engine = sandbox.wrap_runtime_engine(_FakeRuntimeEngine(["filesystem_write"]))

    res = shadow_engine.execute("io.fs.write_file", {"path": "x.txt", "content": "hi"}, ctx)

    assert res.is_success()
    assert res.outputs["shadow"] is True

    report = sandbox.get_report()
    assert len(report.ops) == 1
    op = report.ops[0]
    assert op.capability_id == "io.fs.write_file"
    assert op.params["path"] == "x.txt"
    assert "filesystem_write" in op.side_effects

    assert not (tmp_path / "x.txt").exists()
