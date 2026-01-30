from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict

from runtime.workflow.awe.watchdog import WorkflowWatchdog
from runtime.workflow.engine import StepExecutionResult, WorkflowEngine, WorkflowExecutionContext
from specs.v3.workflow_schema import WorkflowMetadata, WorkflowSpec, WorkflowStep


@dataclass
class _FakeHandler:
    contracts: Dict[str, Any]


class _FakeRegistry:
    def __init__(self):
        self._handler = _FakeHandler(contracts={"side_effects": []})

    def get_handler(self, capability_id: str) -> _FakeHandler:
        return self._handler


class _FakeRuntimeEngine:
    def __init__(self):
        self.registry = _FakeRegistry()

    def execute(self, capability_id: str, params: Dict[str, Any], context: Any):
        raise AssertionError("should not reach execute when watchdog expired")


def test_workflow_engine_watchdog_blocks_step_when_expired() -> None:
    t0 = datetime(2020, 1, 1, 0, 0, 0)
    now = t0

    def time_fn() -> datetime:
        return now

    wd = WorkflowWatchdog(time_fn=time_fn)

    spec = WorkflowSpec(
        name="wf",
        version="1.0.0",
        description="",
        steps=[
            WorkflowStep(
                name="s1",
                agent_name="agent:demo",
                capability_name="io.fs.read_file",
                inputs={},
            )
        ],
        initial_state={},
        metadata=WorkflowMetadata(owner="agent:owner"),
    )
    wf_id = spec.metadata.workflow_id

    wd.register(workflow_id=wf_id, ttl_seconds=1)
    now = now + timedelta(seconds=2)

    ctx = WorkflowExecutionContext(spec)
    engine = WorkflowEngine(runtime_engine=_FakeRuntimeEngine(), execution_context=None)
    engine.watchdog = wd

    result = engine._execute_step(ctx, spec.steps[0])
    assert result == StepExecutionResult.FAILURE
    assert ctx.failed_steps == ["s1"]
