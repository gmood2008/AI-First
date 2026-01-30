import pytest

from runtime.workflow.awe.state_machine import AWEState, AWEStateMachine, InvalidTransitionError


def test_awe_state_machine_happy_path() -> None:
    sm = AWEStateMachine()
    assert sm.state == AWEState.PROVISIONAL

    sm.transition(AWEState.PLANNING)
    sm.transition(AWEState.SHADOW_RUN)
    sm.transition(AWEState.USER_HANDSHAKE)
    sm.transition(AWEState.EXECUTING)
    sm.transition(AWEState.COMPLETED)

    assert sm.state == AWEState.COMPLETED


def test_awe_state_machine_rejects_invalid_transition() -> None:
    sm = AWEStateMachine()

    with pytest.raises(InvalidTransitionError):
        sm.transition(AWEState.EXECUTING)


def test_awe_state_machine_hooks_can_block_transition() -> None:
    sm = AWEStateMachine()

    def guard(t):
        if t.to_state == AWEState.SHADOW_RUN and not t.context.get("allow_shadow"):
            raise RuntimeError("shadow_run_not_allowed")

    sm.add_before_hook(guard)

    sm.transition(AWEState.PLANNING)

    with pytest.raises(RuntimeError, match="shadow_run_not_allowed"):
        sm.transition(AWEState.SHADOW_RUN, context={"allow_shadow": False})

    sm.transition(AWEState.SHADOW_RUN, context={"allow_shadow": True})
    assert sm.state == AWEState.SHADOW_RUN
