import asyncio

from runtime.types import ActionOutput
from runtime.workflow.awe.parallel_executor import ParallelRollbackExecutor


def test_parallel_executor_rolls_back_completed_tasks_on_failure() -> None:
    log: list[str] = []

    async def ok_task(name: str) -> ActionOutput:
        await asyncio.sleep(0.02)

        def undo() -> None:
            log.append(f"undo:{name}")

        log.append(f"done:{name}")
        return ActionOutput(result={"ok": True}, undo_closure=undo)

    async def fail_task() -> ActionOutput:
        await asyncio.sleep(0.01)
        raise RuntimeError("boom")

    ex = ParallelRollbackExecutor()

    res = asyncio.run(
        ex.run([
            lambda: ok_task("a"),
            lambda: ok_task("b"),
            fail_task,
        ])
    )

    assert res.success is False
    assert any(s.startswith("done:") for s in log)
    assert any(s.startswith("undo:") for s in log)


def test_parallel_executor_no_rollback_when_all_succeed() -> None:
    log: list[str] = []

    async def ok_task(name: str) -> ActionOutput:
        await asyncio.sleep(0.01)

        def undo() -> None:
            log.append(f"undo:{name}")

        log.append(f"done:{name}")
        return ActionOutput(result={"ok": True}, undo_closure=undo)

    ex = ParallelRollbackExecutor()

    res = asyncio.run(ex.run([lambda: ok_task("a"), lambda: ok_task("b")]))

    assert res.success is True
    assert log == ["done:a", "done:b"]
