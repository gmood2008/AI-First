from datetime import datetime, timedelta

import pytest

from runtime.workflow.awe.watchdog import WatchdogTimeoutError, WorkflowWatchdog


def test_watchdog_triggers_timeout_and_calls_hook() -> None:
    now = datetime(2020, 1, 1, 0, 0, 0)

    def time_fn() -> datetime:
        return now

    wd = WorkflowWatchdog(time_fn=time_fn)

    called = {}

    def on_timeout(workflow_id: str, payload):
        called["id"] = workflow_id
        called["payload"] = payload

    wd.set_on_timeout(on_timeout)
    wd.register(workflow_id="wf1", ttl_seconds=10, metadata={"a": 1})

    now = now + timedelta(seconds=11)

    with pytest.raises(WatchdogTimeoutError):
        wd.enforce_not_expired(workflow_id="wf1", metadata={"b": 2})

    assert called["id"] == "wf1"
    assert called["payload"]["metadata"]["a"] == 1
    assert called["payload"]["metadata"]["b"] == 2
