from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, List, Optional, Tuple

from runtime.types import ActionOutput


@dataclass(frozen=True)
class ParallelRunResult:
    success: bool
    results: List[Optional[ActionOutput]]
    error: Optional[BaseException] = None


class ParallelRollbackExecutor:
    def __init__(self) -> None:
        pass

    async def run(
        self,
        tasks: List[Callable[[], Awaitable[ActionOutput]]],
    ) -> ParallelRunResult:
        completion_order: List[int] = []

        async def _wrapped(i: int) -> ActionOutput:
            out = await tasks[i]()
            completion_order.append(i)
            return out

        coros = [_wrapped(i) for i in range(len(tasks))]
        gathered = await asyncio.gather(*coros, return_exceptions=True)

        results: List[Optional[ActionOutput]] = [None for _ in range(len(tasks))]
        first_error: Optional[BaseException] = None

        for i, r in enumerate(gathered):
            if isinstance(r, BaseException):
                if first_error is None:
                    first_error = r
                continue
            results[i] = r

        if first_error is not None:
            self._rollback(results=results, completion_order=completion_order)
            return ParallelRunResult(success=False, results=results, error=first_error)

        return ParallelRunResult(success=True, results=results)

    def _rollback(self, *, results: List[Optional[ActionOutput]], completion_order: List[int]) -> None:
        for i in reversed(completion_order):
            out = results[i]
            if out is None:
                continue
            if out.undo_closure is None:
                continue
            try:
                out.undo_closure()
            except Exception:
                continue
