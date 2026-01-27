"""
Runtime Mission Control API - The Execution Entry

Purpose: SREs have emergency brake control to pause/resume workflows.
Power: Can pause/resume workflows (control state).
Constraint: Cannot modify workflow steps (control content).
"""

from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum

app = FastAPI(
    title="Runtime Mission Control API",
    description="Emergency control interface for SREs to manage workflow execution",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

security = HTTPBearer()


# ==================== Models ====================

class WorkflowStatus(str, Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SUSPENDED = "SUSPENDED"  # Suspended by governance


class WorkflowSummary(BaseModel):
    """Summary of a workflow"""
    workflow_id: UUID
    name: str
    status: WorkflowStatus
    started_at: datetime
    current_step: str
    total_steps: int
    completed_steps: int
    agent_id: str


class WorkflowDetail(BaseModel):
    """Detailed view of a workflow"""
    workflow_id: UUID
    name: str
    status: WorkflowStatus
    started_at: datetime
    updated_at: datetime
    current_step: str
    total_steps: int
    completed_steps: int
    agent_id: str
    steps: List[Dict[str, Any]]
    trace_id: Optional[str] = None


class ControlRequest(BaseModel):
    """Request to control a workflow"""
    workflow_id: UUID
    action: Literal["PAUSE", "RESUME"]
    reason: str = Field(..., description="Reason for the control action")
    emergency: bool = Field(False, description="Whether this is an emergency action")


class ControlResponse(BaseModel):
    """Response after a control action"""
    workflow_id: UUID
    action: str
    previous_status: WorkflowStatus
    new_status: WorkflowStatus
    controlled_by: str
    controlled_at: datetime
    audit_event_id: UUID


class TraceEntry(BaseModel):
    """An entry in the execution trace"""
    trace_id: str
    timestamp: datetime
    component: str
    event: str
    data: Dict[str, Any]


class HealthStatus(BaseModel):
    """Runtime health status"""
    status: str
    uptime_seconds: int
    active_workflows: int
    paused_workflows: int
    total_workflows_executed: int
    average_execution_time_ms: float
    last_health_check: datetime


# ==================== Mock Data Store ====================

MOCK_WORKFLOWS = {
    UUID("30000000-0000-0000-0000-000000000001"): {
        "name": "Customer Onboarding Flow",
        "status": WorkflowStatus.RUNNING,
        "started_at": datetime(2026, 1, 25, 14, 0, 0),
        "updated_at": datetime(2026, 1, 25, 14, 5, 0),
        "current_step": "verify_identity",
        "total_steps": 5,
        "completed_steps": 2,
        "agent_id": "agent-001",
        "steps": [
            {"step_id": 1, "name": "collect_info", "status": "COMPLETED"},
            {"step_id": 2, "name": "verify_email", "status": "COMPLETED"},
            {"step_id": 3, "name": "verify_identity", "status": "IN_PROGRESS"},
            {"step_id": 4, "name": "create_account", "status": "PENDING"},
            {"step_id": 5, "name": "send_welcome", "status": "PENDING"},
        ],
        "trace_id": "trace-001",
    },
    UUID("30000000-0000-0000-0000-000000000002"): {
        "name": "Financial Transaction Processing",
        "status": WorkflowStatus.SUSPENDED,
        "started_at": datetime(2026, 1, 25, 13, 30, 0),
        "updated_at": datetime(2026, 1, 25, 13, 45, 0),
        "current_step": "execute_transfer",
        "total_steps": 4,
        "completed_steps": 2,
        "agent_id": "agent-002",
        "steps": [
            {"step_id": 1, "name": "validate_request", "status": "COMPLETED"},
            {"step_id": 2, "name": "check_limits", "status": "COMPLETED"},
            {"step_id": 3, "name": "execute_transfer", "status": "SUSPENDED"},
            {"step_id": 4, "name": "send_confirmation", "status": "PENDING"},
        ],
        "trace_id": "trace-002",
    },
}

MOCK_TRACES = {
    "trace-001": [
        {
            "trace_id": "trace-001",
            "timestamp": datetime(2026, 1, 25, 14, 0, 0),
            "component": "RUNTIME",
            "event": "WORKFLOW_STARTED",
            "data": {"workflow_id": "30000000-0000-0000-0000-000000000001"},
        },
        {
            "trace_id": "trace-001",
            "timestamp": datetime(2026, 1, 25, 14, 2, 0),
            "component": "K-OS",
            "event": "PERMISSION_GRANTED",
            "data": {"capability": "collect_customer_info"},
        },
    ],
    "trace-002": [
        {
            "trace_id": "trace-002",
            "timestamp": datetime(2026, 1, 25, 13, 30, 0),
            "component": "RUNTIME",
            "event": "WORKFLOW_STARTED",
            "data": {"workflow_id": "30000000-0000-0000-0000-000000000002"},
        },
        {
            "trace_id": "trace-002",
            "timestamp": datetime(2026, 1, 25, 13, 45, 0),
            "component": "K-OS",
            "event": "PERMISSION_SUSPENDED",
            "data": {"capability": "execute_large_transfer", "reason": "EXCEEDS_LIMIT"},
        },
    ],
}


# ==================== Authentication ====================

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, str]:
    """
    Verify JWT token and extract user information.
    
    Returns: User info dict with user_id and role
    """
    token = credentials.credentials
    
    # Mock validation: accept tokens starting with "runtime_"
    if not token.startswith("runtime_"):
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Extract mock user info from token
    if token == "runtime_admin":
        return {"user_id": "sre_admin@k-os.ai", "role": "sre_admin"}
    else:
        return {"user_id": "sre@k-os.ai", "role": "sre"}


# ==================== Audit Event Logging ====================

class AuditEvent(BaseModel):
    """Audit event for runtime control actions"""
    event_id: UUID
    event_type: Literal["RUNTIME_CONTROL"]
    timestamp: datetime
    user_id: str
    user_role: str
    action: str
    target_type: str
    target_id: UUID
    reason: str
    metadata: Dict[str, Any]


AUDIT_LOG = []


def log_audit_event(
    user_info: Dict[str, str],
    action: str,
    target_id: UUID,
    reason: str,
    metadata: Dict[str, Any]
) -> UUID:
    """Log an audit event"""
    event_id = uuid4()
    
    event = AuditEvent(
        event_id=event_id,
        event_type="RUNTIME_CONTROL",
        timestamp=datetime.now(),
        user_id=user_info["user_id"],
        user_role=user_info["role"],
        action=action,
        target_type="workflow",
        target_id=target_id,
        reason=reason,
        metadata=metadata,
    )
    
    AUDIT_LOG.append(event)
    print(f"🚨 Runtime Control Event: {action} by {event.user_id} on workflow {target_id}")
    
    return event_id


# ==================== API Endpoints ====================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Runtime Mission Control API",
        "status": "operational",
        "version": "1.0.0",
        "mode": "control",
    }


@app.get("/v1/workflows", response_model=List[WorkflowSummary])
async def list_workflows(
    status: Optional[WorkflowStatus] = None,
    user_info: Dict[str, str] = Depends(verify_token)
) -> List[WorkflowSummary]:
    """
    List all active workflows.
    
    Query Parameters:
    - status: Filter by workflow status
    
    Returns: List of workflow summaries
    """
    workflows = []
    
    for wf_id, wf_data in MOCK_WORKFLOWS.items():
        if status and wf_data["status"] != status:
            continue
        
        workflows.append(WorkflowSummary(
            workflow_id=wf_id,
            name=wf_data["name"],
            status=wf_data["status"],
            started_at=wf_data["started_at"],
            current_step=wf_data["current_step"],
            total_steps=wf_data["total_steps"],
            completed_steps=wf_data["completed_steps"],
            agent_id=wf_data["agent_id"],
        ))
    
    return workflows


@app.get("/v1/workflows/{workflow_id}", response_model=WorkflowDetail)
async def get_workflow(
    workflow_id: UUID,
    user_info: Dict[str, str] = Depends(verify_token)
) -> WorkflowDetail:
    """
    Get detailed information about a specific workflow.
    
    Path Parameters:
    - workflow_id: UUID of the workflow
    
    Returns: Detailed workflow information
    """
    if workflow_id not in MOCK_WORKFLOWS:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    wf_data = MOCK_WORKFLOWS[workflow_id]
    
    return WorkflowDetail(
        workflow_id=workflow_id,
        name=wf_data["name"],
        status=wf_data["status"],
        started_at=wf_data["started_at"],
        updated_at=wf_data["updated_at"],
        current_step=wf_data["current_step"],
        total_steps=wf_data["total_steps"],
        completed_steps=wf_data["completed_steps"],
        agent_id=wf_data["agent_id"],
        steps=wf_data["steps"],
        trace_id=wf_data.get("trace_id"),
    )


@app.post("/v1/workflows/{workflow_id}/pause", response_model=ControlResponse)
async def pause_workflow(
    workflow_id: UUID,
    request: ControlRequest,
    user_info: Dict[str, str] = Depends(verify_token)
) -> ControlResponse:
    """
    Pause a running workflow (emergency brake).
    
    This is the "red button" that SREs can press to stop a workflow.
    The workflow state is preserved and can be resumed later.
    
    Path Parameters:
    - workflow_id: UUID of the workflow to pause
    
    Request Body:
    - reason: Why the workflow is being paused
    - emergency: Whether this is an emergency action
    
    Returns: Control response with audit event ID
    """
    if workflow_id not in MOCK_WORKFLOWS:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    wf_data = MOCK_WORKFLOWS[workflow_id]
    previous_status = wf_data["status"]
    
    # Validate state transition
    if previous_status not in [WorkflowStatus.RUNNING, WorkflowStatus.SUSPENDED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot pause workflow in {previous_status} status"
        )
    
    # Update workflow status
    wf_data["status"] = WorkflowStatus.PAUSED
    wf_data["updated_at"] = datetime.now()
    
    controlled_at = datetime.now()
    
    # Log audit event
    audit_event_id = log_audit_event(
        user_info=user_info,
        action="PAUSE",
        target_id=workflow_id,
        reason=request.reason,
        metadata={
            "emergency": request.emergency,
            "previous_status": previous_status.value,
            "workflow_name": wf_data["name"],
        }
    )
    
    return ControlResponse(
        workflow_id=workflow_id,
        action="PAUSE",
        previous_status=previous_status,
        new_status=WorkflowStatus.PAUSED,
        controlled_by=user_info["user_id"],
        controlled_at=controlled_at,
        audit_event_id=audit_event_id,
    )


@app.post("/v1/workflows/{workflow_id}/resume", response_model=ControlResponse)
async def resume_workflow(
    workflow_id: UUID,
    request: ControlRequest,
    user_info: Dict[str, str] = Depends(verify_token)
) -> ControlResponse:
    """
    Resume a paused workflow.
    
    The workflow will continue from where it was paused.
    
    Path Parameters:
    - workflow_id: UUID of the workflow to resume
    
    Request Body:
    - reason: Why the workflow is being resumed
    
    Returns: Control response with audit event ID
    """
    if workflow_id not in MOCK_WORKFLOWS:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    wf_data = MOCK_WORKFLOWS[workflow_id]
    previous_status = wf_data["status"]
    
    # Validate state transition
    if previous_status != WorkflowStatus.PAUSED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot resume workflow in {previous_status} status"
        )
    
    # Update workflow status
    wf_data["status"] = WorkflowStatus.RUNNING
    wf_data["updated_at"] = datetime.now()
    
    controlled_at = datetime.now()
    
    # Log audit event
    audit_event_id = log_audit_event(
        user_info=user_info,
        action="RESUME",
        target_id=workflow_id,
        reason=request.reason,
        metadata={
            "previous_status": previous_status.value,
            "workflow_name": wf_data["name"],
        }
    )
    
    return ControlResponse(
        workflow_id=workflow_id,
        action="RESUME",
        previous_status=previous_status,
        new_status=WorkflowStatus.RUNNING,
        controlled_by=user_info["user_id"],
        controlled_at=controlled_at,
        audit_event_id=audit_event_id,
    )


@app.get("/v1/workflows/{workflow_id}/trace", response_model=List[TraceEntry])
async def get_workflow_trace(
    workflow_id: UUID,
    user_info: Dict[str, str] = Depends(verify_token)
) -> List[TraceEntry]:
    """
    Get the execution trace for a workflow.
    
    This shows all events that occurred during workflow execution,
    including K-OS permission checks and Runtime state changes.
    
    Path Parameters:
    - workflow_id: UUID of the workflow
    
    Returns: List of trace entries
    """
    if workflow_id not in MOCK_WORKFLOWS:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    wf_data = MOCK_WORKFLOWS[workflow_id]
    trace_id = wf_data.get("trace_id")
    
    if not trace_id or trace_id not in MOCK_TRACES:
        return []
    
    return [TraceEntry(**entry) for entry in MOCK_TRACES[trace_id]]


@app.get("/v1/health", response_model=HealthStatus)
async def get_health(
    user_info: Dict[str, str] = Depends(verify_token)
) -> HealthStatus:
    """
    Get Runtime health status.
    
    Returns: Health metrics
    """
    active = sum(1 for wf in MOCK_WORKFLOWS.values() if wf["status"] == WorkflowStatus.RUNNING)
    paused = sum(1 for wf in MOCK_WORKFLOWS.values() if wf["status"] == WorkflowStatus.PAUSED)
    
    return HealthStatus(
        status="healthy",
        uptime_seconds=3600,  # Mock value
        active_workflows=active,
        paused_workflows=paused,
        total_workflows_executed=127,  # Mock value
        average_execution_time_ms=2500.0,  # Mock value
        last_health_check=datetime.now(),
    )


# ==================== Startup Event ====================

@app.on_event("startup")
async def startup_event():
    """Initialize the API on startup"""
    print("🎮 Runtime Mission Control API starting...")
    print("🚨 Mode: Emergency Control")
    print("🔒 Authentication: JWT Bearer Token")
    print("📝 Audit Logging: Enabled")
    print("⚠️  Constraint: Can control state, NOT content")
    print("✅ Ready to serve")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8030)
