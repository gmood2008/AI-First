from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional


class WatchdogTimeoutError(RuntimeError):
    pass


TimeFn = Callable[[], datetime]
TimeoutHook = Callable[[str, Dict[str, Any]], None]


@dataclass
class WatchdogRecord:
    workflow_id: str
    ttl_seconds: int
    started_at: datetime
    last_heartbeat_at: datetime
    metadata: Dict[str, Any]


class WorkflowWatchdog:
    def __init__(self, *, time_fn: Optional[TimeFn] = None) -> None:
        self._time_fn: TimeFn = time_fn or datetime.utcnow
        self._records: Dict[str, WatchdogRecord] = {}
        self._on_timeout: Optional[TimeoutHook] = None

    def set_on_timeout(self, hook: TimeoutHook) -> None:
        self._on_timeout = hook

    def register(self, *, workflow_id: str, ttl_seconds: int, metadata: Optional[Dict[str, Any]] = None) -> None:
        now = self._time_fn()
        self._records[workflow_id] = WatchdogRecord(
            workflow_id=workflow_id,
            ttl_seconds=int(ttl_seconds),
            started_at=now,
            last_heartbeat_at=now,
            metadata=metadata or {},
        )

    def heartbeat(self, *, workflow_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        rec = self._records.get(workflow_id)
        if rec is None:
            return

        now = self._time_fn()
        rec.last_heartbeat_at = now
        if metadata:
            rec.metadata.update(metadata)

    def is_expired(self, *, workflow_id: str) -> bool:
        rec = self._records.get(workflow_id)
        if rec is None:
            return False

        now = self._time_fn()
        deadline = rec.started_at + timedelta(seconds=rec.ttl_seconds)
        return now >= deadline

    def enforce_not_expired(self, *, workflow_id: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        if not self.is_expired(workflow_id=workflow_id):
            return

        rec = self._records.get(workflow_id)
        payload: Dict[str, Any] = {
            "workflow_id": workflow_id,
            "ttl_seconds": rec.ttl_seconds if rec else None,
            "metadata": {**(rec.metadata if rec else {}), **(metadata or {})},
        }

        if self._on_timeout:
            try:
                self._on_timeout(workflow_id, payload)
            except Exception:
                pass

        raise WatchdogTimeoutError(f"Workflow {workflow_id} exceeded TTL")
