import asyncio

import pytest

from runtime.types import ActionOutput
from runtime.workflow.awe import CycleDetectedError, ExecutionGraph, ExecutionGraphRunner, Link, Task, Workflow


def test_execution_graph_levels_parallel_then_join() -> None:
    wf = Workflow(
        workflow_id="wf",
        tasks=[
            Task(task_id="a"),
            Task(task_id="b"),
            Task(task_id="c"),
        ],
        links=[
            Link(source="a", target="c", kind="depends_on"),
            Link(source="b", target="c", kind="depends_on"),
        ],
    )

    g = ExecutionGraph.from_workflow(wf)
    levels = g.levels()

    assert levels[0].task_ids == ["a", "b"]
    assert levels[1].task_ids == ["c"]


def test_execution_graph_detects_cycle() -> None:
    wf = Workflow(
        workflow_id="wf",
        tasks=[Task(task_id="a"), Task(task_id="b")],
        links=[
            Link(source="a", target="b"),
            Link(source="b", target="a"),
        ],
    )

    g = ExecutionGraph.from_workflow(wf)
    with pytest.raises(CycleDetectedError):
        g.levels()


def test_execution_graph_runner_rolls_back_on_failure() -> None:
    log: list[str] = []

    wf = Workflow(
        workflow_id="wf",
        tasks=[Task(task_id="a"), Task(task_id="b")],
        links=[],
    )

    async def runner(t: Task) -> ActionOutput:
        if t.task_id == "b":
            await asyncio.sleep(0.01)
            raise RuntimeError("boom")

        await asyncio.sleep(0.02)

        def undo() -> None:
            log.append("undo:a")

        log.append("done:a")
        return ActionOutput(result={"ok": True}, undo_closure=undo)

    r = ExecutionGraphRunner()

    with pytest.raises(RuntimeError):
        asyncio.run(r.run(wf, runner=runner))

    # a may complete before b fails; it must be rolled back
    assert "done:a" in log
    assert "undo:a" in log
