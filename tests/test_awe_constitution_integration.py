from dataclasses import dataclass
from typing import Any, Dict, List

from runtime.workflow.awe.constitution import ConstitutionEngine
from runtime.workflow.engine import StepExecutionResult, WorkflowEngine, WorkflowExecutionContext
from specs.v3.workflow_schema import WorkflowMetadata, WorkflowSpec, WorkflowStep


@dataclass
class _FakeHandler:
    contracts: Dict[str, Any]


class _FakeRegistry:
    def __init__(self, handler: _FakeHandler):
        self._handler = handler

    def get_handler(self, capability_id: str) -> _FakeHandler:
        return self._handler


class _FakeRuntimeEngine:
    def __init__(self, side_effects: List[str]):
        self.registry = _FakeRegistry(_FakeHandler(contracts={"side_effects": side_effects}))


def test_workflow_engine_constitution_can_block_step_execution() -> None:
    spec = WorkflowSpec(
        name="wf",
        version="1.0.0",
        description="",
        steps=[
            WorkflowStep(
                name="write",
                agent_name="agent:demo",
                capability_name="io.fs.write_file",
                inputs={},
            )
        ],
        initial_state={},
        metadata=WorkflowMetadata(owner="agent:owner"),
    )

    ctx = WorkflowExecutionContext(spec)
    step = spec.steps[0]

    engine = WorkflowEngine(
        runtime_engine=_FakeRuntimeEngine(["filesystem_write"]),
        execution_context=None,
        policy_engine=None,
        persistence=None,
        approval_manager=None,
        pack_registry=None,
    )
    engine.constitution_engine = ConstitutionEngine(mode="strict")

    result = engine._execute_step(ctx, step)

    assert result == StepExecutionResult.FAILURE
    assert ctx.failed_steps == ["write"]
