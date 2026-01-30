from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

from runtime.types import ActionOutput

from .domain import Link, Task, Workflow
from .parallel_executor import ParallelRollbackExecutor


class CycleDetectedError(RuntimeError):
    pass


@dataclass(frozen=True)
class GraphLevel:
    task_ids: List[str]


class ExecutionGraph:
    def __init__(self, *, tasks: Dict[str, Task], deps: Dict[str, Set[str]]):
        self.tasks = tasks
        self.deps = deps

    @classmethod
    def from_workflow(cls, wf: Workflow) -> "ExecutionGraph":
        tasks: Dict[str, Task] = {t.task_id: t for t in wf.tasks}
        deps: Dict[str, Set[str]] = {tid: set() for tid in tasks.keys()}

        for link in wf.links:
            _apply_link(tasks=tasks, deps=deps, link=link)

        return cls(tasks=tasks, deps=deps)

    def levels(self) -> List[GraphLevel]:
        deps = {k: set(v) for k, v in self.deps.items()}
        ready = sorted([tid for tid, d in deps.items() if not d])
        levels: List[GraphLevel] = []

        remaining = set(deps.keys())

        while remaining:
            if not ready:
                raise CycleDetectedError("No runnable tasks (cycle detected)")

            current = ready
            levels.append(GraphLevel(task_ids=current))

            for tid in current:
                remaining.remove(tid)
                deps.pop(tid, None)

            # remove satisfied deps
            for tid, d in deps.items():
                d.difference_update(set(current))

            ready = sorted([tid for tid, d in deps.items() if not d])

        return levels


TaskRunner = Callable[[Task], Awaitable[ActionOutput]]


class ExecutionGraphRunner:
    def __init__(self, *, parallel_executor: Optional[ParallelRollbackExecutor] = None):
        self._parallel = parallel_executor or ParallelRollbackExecutor()

    async def run(self, wf: Workflow, *, runner: TaskRunner) -> Dict[str, ActionOutput]:
        graph = ExecutionGraph.from_workflow(wf)
        outputs: Dict[str, ActionOutput] = {}

        for level in graph.levels():
            # run tasks in the same level concurrently
            tasks = [graph.tasks[tid] for tid in level.task_ids]

            async def _call(t: Task) -> ActionOutput:
                out = await runner(t)
                return out

            wrapped: List[Callable[[], Awaitable[ActionOutput]]] = [
                (lambda t=t: _call(t)) for t in tasks
            ]

            res = await self._parallel.run(wrapped)
            if not res.success:
                # rollback already handled by ParallelRollbackExecutor
                raise RuntimeError(f"ExecutionGraphRunner failed: {res.error}")

            for tid, out in zip(level.task_ids, res.results, strict=True):
                if out is None:
                    raise RuntimeError("Missing ActionOutput")
                outputs[tid] = out

        return outputs


def _apply_link(*, tasks: Dict[str, Task], deps: Dict[str, Set[str]], link: Link) -> None:
    if link.source not in tasks or link.target not in tasks:
        return

    kind = (link.kind or "").strip() or "depends_on"

    # default semantics: target depends on source
    if kind in {"depends_on", "dependency"}:
        deps.setdefault(link.target, set()).add(link.source)
        return

    # containment doesn't affect scheduling
    if kind in {"contains", "child"}:
        return

    # fallback to depends_on semantics
    deps.setdefault(link.target, set()).add(link.source)
