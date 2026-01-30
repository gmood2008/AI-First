from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class AWEState(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    PLANNING = "PLANNING"
    SHADOW_RUN = "SHADOW_RUN"
    USER_HANDSHAKE = "USER_HANDSHAKE"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    PANIC = "PANIC"


class InvalidTransitionError(RuntimeError):
    pass


Hook = Callable[["Transition"], None]


@dataclass(frozen=True)
class Transition:
    from_state: AWEState
    to_state: AWEState
    context: Dict[str, Any]


class AWEStateMachine:
    def __init__(
        self,
        initial: AWEState = AWEState.PROVISIONAL,
        transitions: Optional[Dict[AWEState, List[AWEState]]] = None,
    ):
        self._state = initial
        self._transitions = transitions or {
            AWEState.PROVISIONAL: [AWEState.PLANNING, AWEState.PANIC],
            AWEState.PLANNING: [AWEState.SHADOW_RUN, AWEState.PANIC],
            AWEState.SHADOW_RUN: [AWEState.USER_HANDSHAKE, AWEState.PANIC],
            AWEState.USER_HANDSHAKE: [AWEState.EXECUTING, AWEState.PANIC],
            AWEState.EXECUTING: [AWEState.COMPLETED, AWEState.PANIC],
            AWEState.COMPLETED: [],
            AWEState.PANIC: [],
        }

        self._before_any: List[Hook] = []
        self._after_any: List[Hook] = []
        self._before: Dict[Tuple[AWEState, AWEState], List[Hook]] = {}
        self._after: Dict[Tuple[AWEState, AWEState], List[Hook]] = {}

    @property
    def state(self) -> AWEState:
        return self._state

    def add_before_hook(self, hook: Hook, *, from_state: Optional[AWEState] = None, to_state: Optional[AWEState] = None) -> None:
        if from_state is None or to_state is None:
            self._before_any.append(hook)
            return
        key = (from_state, to_state)
        self._before.setdefault(key, []).append(hook)

    def add_after_hook(self, hook: Hook, *, from_state: Optional[AWEState] = None, to_state: Optional[AWEState] = None) -> None:
        if from_state is None or to_state is None:
            self._after_any.append(hook)
            return
        key = (from_state, to_state)
        self._after.setdefault(key, []).append(hook)

    def can_transition(self, to_state: AWEState) -> bool:
        allowed = self._transitions.get(self._state, [])
        return to_state in allowed

    def transition(self, to_state: AWEState, *, context: Optional[Dict[str, Any]] = None) -> Transition:
        context = context or {}

        if not self.can_transition(to_state):
            raise InvalidTransitionError(f"Invalid transition {self._state.value} -> {to_state.value}")

        t = Transition(from_state=self._state, to_state=to_state, context=context)

        for hook in self._before_any:
            hook(t)
        for hook in self._before.get((t.from_state, t.to_state), []):
            hook(t)

        self._state = to_state

        for hook in self._after.get((t.from_state, t.to_state), []):
            hook(t)
        for hook in self._after_any:
            hook(t)

        return t
