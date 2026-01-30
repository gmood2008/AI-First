from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Literal, Optional
from uuid import UUID, uuid4

try:
    from fastapi import Depends, FastAPI, HTTPException, Security
    from fastapi import Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    from pydantic import BaseModel, Field
    from starlette.responses import StreamingResponse
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "FastAPI is required for runtime.api. Install optional deps: pip install -e .[api]"
    ) from e

from runtime.audit.logger import AuditLogger
from runtime.workflow.persistence import WorkflowPersistence, WorkflowStatus as PersistedWorkflowStatus


class WorkflowStatus(str, Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    PENDING = "PENDING"


class WorkflowSummary(BaseModel):
    workflow_id: str
    name: str
    status: WorkflowStatus
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    completed_steps: Optional[int] = None
    owner: Optional[str] = None


class WorkflowDetail(BaseModel):
    workflow_id: str
    name: str
    status: WorkflowStatus
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    spec_yaml: Optional[str] = None
    error_message: Optional[str] = None
    rollback_reason: Optional[str] = None


class ControlRequest(BaseModel):
    workflow_id: str
    action: Literal["PAUSE", "RESUME"]
    reason: str = Field(...)
    emergency: bool = Field(False)


class ControlResponse(BaseModel):
    workflow_id: str
    action: str
    previous_status: WorkflowStatus
    new_status: WorkflowStatus
    controlled_by: str
    controlled_at: str
    audit_event_id: str


class HealthStatus(BaseModel):
    status: str
    uptime_seconds: int
    last_health_check: str


security = HTTPBearer()


def _require_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, str]:
    expected = os.getenv("AIF_RUNTIME_API_TOKEN")
    if not expected:
        raise HTTPException(status_code=500, detail="AIF_RUNTIME_API_TOKEN not configured")

    token = credentials.credentials
    if token != expected:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"user_id": "api", "role": "sre"}


def _to_api_status(raw: str) -> WorkflowStatus:
    m = {
        PersistedWorkflowStatus.PENDING.value: WorkflowStatus.PENDING,
        PersistedWorkflowStatus.RUNNING.value: WorkflowStatus.RUNNING,
        PersistedWorkflowStatus.PAUSED.value: WorkflowStatus.PAUSED,
        PersistedWorkflowStatus.COMPLETED.value: WorkflowStatus.COMPLETED,
        PersistedWorkflowStatus.FAILED.value: WorkflowStatus.FAILED,
        PersistedWorkflowStatus.ROLLED_BACK.value: WorkflowStatus.ROLLED_BACK,
    }
    return m.get(raw, WorkflowStatus.FAILED)


def _to_persisted_status(raw: WorkflowStatus) -> PersistedWorkflowStatus:
    m = {
        WorkflowStatus.PENDING: PersistedWorkflowStatus.PENDING,
        WorkflowStatus.RUNNING: PersistedWorkflowStatus.RUNNING,
        WorkflowStatus.PAUSED: PersistedWorkflowStatus.PAUSED,
        WorkflowStatus.COMPLETED: PersistedWorkflowStatus.COMPLETED,
        WorkflowStatus.FAILED: PersistedWorkflowStatus.FAILED,
        WorkflowStatus.ROLLED_BACK: PersistedWorkflowStatus.ROLLED_BACK,
    }
    return m[raw]


@dataclass
class _EventBus:
    subscribers: List["asyncio.Queue[str]"]

    def __init__(self):
        import asyncio

        self.subscribers = []
        self._asyncio = asyncio

    async def publish(self, data: str) -> None:
        for q in list(self.subscribers):
            try:
                q.put_nowait(data)
            except Exception:
                continue

    async def subscribe(self) -> AsyncIterator[str]:
        q = self._asyncio.Queue()
        self.subscribers.append(q)
        try:
            while True:
                item = await q.get()
                yield item
        finally:
            try:
                self.subscribers.remove(q)
            except ValueError:
                pass


_bus = _EventBus()
_started_at = datetime.utcnow()


def create_app(
    *,
    persistence: Optional[WorkflowPersistence] = None,
    audit_logger: Optional[AuditLogger] = None,
) -> FastAPI:
    app = FastAPI(
        title="Runtime Mission Control API",
        description="Emergency control interface for SREs to manage workflow execution",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    app.state._workflow_persistence = persistence
    app.state._audit_logger = audit_logger

    def _get_persistence(request: Request) -> WorkflowPersistence:
        existing = getattr(request.app.state, "_workflow_persistence", None)
        if existing is not None:
            return existing
        p = WorkflowPersistence(db_path=os.getenv("AIF_RUNTIME_DB"))
        request.app.state._workflow_persistence = p
        return p

    def _get_audit_logger(request: Request) -> AuditLogger:
        existing = getattr(request.app.state, "_audit_logger", None)
        if existing is not None:
            return existing
        logger = AuditLogger(db_path=os.path.expanduser("~/.ai-first/audit.db"))
        request.app.state._audit_logger = logger
        return logger

    @app.get("/")
    async def root() -> Dict[str, Any]:
        return {"service": "Runtime Mission Control API", "status": "operational", "version": "1.0.0"}

    @app.get("/v1/health", response_model=HealthStatus)
    async def health(user_info: Dict[str, str] = Depends(_require_token)) -> HealthStatus:
        _ = user_info
        uptime = int((datetime.utcnow() - _started_at).total_seconds())
        return HealthStatus(status="healthy", uptime_seconds=uptime, last_health_check=datetime.utcnow().isoformat())

    @app.get("/v1/workflows", response_model=List[WorkflowSummary])
    async def list_workflows(
        request: Request,
        status: Optional[str] = None,
        user_info: Dict[str, str] = Depends(_require_token),
    ) -> List[WorkflowSummary]:
        _ = user_info

        persistence_local = _get_persistence(request)

        # Minimal listing: return RUNNING/PAUSED by default (same as get_running_workflows)
        rows = persistence_local.get_running_workflows()
        result: List[WorkflowSummary] = []
        for r in rows:
            s = _to_api_status(str(r.get("status") or ""))
            if status and s.value != status:
                continue
            result.append(
                WorkflowSummary(
                    workflow_id=str(r.get("id")),
                    name=str(r.get("name")),
                    status=s,
                    started_at=r.get("started_at"),
                    updated_at=r.get("updated_at"),
                    owner=r.get("owner"),
                )
            )
        return result

    @app.get("/v1/workflows/{workflow_id}", response_model=WorkflowDetail)
    async def get_workflow(
        request: Request,
        workflow_id: str,
        user_info: Dict[str, str] = Depends(_require_token),
    ) -> WorkflowDetail:
        _ = user_info

        persistence_local = _get_persistence(request)
        rec = persistence_local.get_workflow(workflow_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return WorkflowDetail(
            workflow_id=str(rec.get("id")),
            name=str(rec.get("name")),
            status=_to_api_status(str(rec.get("status") or "")),
            created_at=rec.get("created_at"),
            updated_at=rec.get("updated_at"),
            started_at=rec.get("started_at"),
            completed_at=rec.get("completed_at"),
            spec_yaml=rec.get("spec_yaml"),
            error_message=rec.get("error_message"),
            rollback_reason=rec.get("rollback_reason"),
        )

    @app.post("/v1/workflows/{workflow_id}/pause", response_model=ControlResponse)
    async def pause_workflow(
        http_request: Request,
        workflow_id: str,
        request: ControlRequest,
        user_info: Dict[str, str] = Depends(_require_token),
    ) -> ControlResponse:
        persistence_local = _get_persistence(http_request)
        audit_logger_local = _get_audit_logger(http_request)

        rec = persistence_local.get_workflow(workflow_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Workflow not found")

        prev = _to_api_status(str(rec.get("status") or ""))
        if prev not in {WorkflowStatus.RUNNING, WorkflowStatus.PAUSED, WorkflowStatus.PENDING}:
            raise HTTPException(status_code=400, detail=f"Cannot pause workflow in {prev.value}")

        persistence_local.update_workflow_status(
            workflow_id=workflow_id,
            status=_to_persisted_status(WorkflowStatus.PAUSED),
            rollback_reason=request.reason,
        )

        audit_event_id = str(uuid4())
        audit_logger_local.log_action(
            session_id=workflow_id,
            user_id=user_info["user_id"],
            capability_id="api.mission_control.pause",
            action_type="control",
            params={"workflow_id": workflow_id, "reason": request.reason, "emergency": request.emergency},
            result={"previous_status": prev.value, "new_status": WorkflowStatus.PAUSED.value, "audit_event_id": audit_event_id},
            status="success",
            side_effects=["workflow_control"],
            requires_confirmation=False,
            undo_available=False,
        )

        await _bus.publish(f"event:workflow\ndata:{workflow_id} paused\n\n")

        return ControlResponse(
            workflow_id=workflow_id,
            action="PAUSE",
            previous_status=prev,
            new_status=WorkflowStatus.PAUSED,
            controlled_by=user_info["user_id"],
            controlled_at=datetime.utcnow().isoformat(),
            audit_event_id=audit_event_id,
        )

    @app.post("/v1/workflows/{workflow_id}/resume", response_model=ControlResponse)
    async def resume_workflow(
        http_request: Request,
        workflow_id: str,
        request: ControlRequest,
        user_info: Dict[str, str] = Depends(_require_token),
    ) -> ControlResponse:
        persistence_local = _get_persistence(http_request)
        audit_logger_local = _get_audit_logger(http_request)

        rec = persistence_local.get_workflow(workflow_id)
        if not rec:
            raise HTTPException(status_code=404, detail="Workflow not found")

        prev = _to_api_status(str(rec.get("status") or ""))
        if prev != WorkflowStatus.PAUSED:
            raise HTTPException(status_code=400, detail=f"Cannot resume workflow in {prev.value}")

        persistence_local.update_workflow_status(
            workflow_id=workflow_id,
            status=_to_persisted_status(WorkflowStatus.RUNNING),
        )

        audit_event_id = str(uuid4())
        audit_logger_local.log_action(
            session_id=workflow_id,
            user_id=user_info["user_id"],
            capability_id="api.mission_control.resume",
            action_type="control",
            params={"workflow_id": workflow_id, "reason": request.reason},
            result={"previous_status": prev.value, "new_status": WorkflowStatus.RUNNING.value, "audit_event_id": audit_event_id},
            status="success",
            side_effects=["workflow_control"],
            requires_confirmation=False,
            undo_available=False,
        )

        await _bus.publish(f"event:workflow\ndata:{workflow_id} resumed\n\n")

        return ControlResponse(
            workflow_id=workflow_id,
            action="RESUME",
            previous_status=prev,
            new_status=WorkflowStatus.RUNNING,
            controlled_by=user_info["user_id"],
            controlled_at=datetime.utcnow().isoformat(),
            audit_event_id=audit_event_id,
        )

    @app.get("/v1/events")
    async def events(user_info: Dict[str, str] = Depends(_require_token)):
        _ = user_info

        async def gen() -> AsyncIterator[bytes]:
            async for item in _bus.subscribe():
                yield item.encode("utf-8")

        return StreamingResponse(gen(), media_type="text/event-stream")

    return app


app = create_app()