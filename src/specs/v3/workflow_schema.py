"""
AI-First Runtime v3.0 - Workflow Specification Schema

This module defines the schema for transactional multi-agent workflows.
A Workflow is the atomic unit of execution, governance, and audit.

Design Principles:
1. Schema-First: Workflow definitions are declarative (YAML/JSON)
2. Transactional: Every workflow is a distributed transaction with ACID-like guarantees
3. Governable: Built-in support for RBAC, human approval, and audit
4. Rollback-Ready: Every step must define its compensation logic
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
import uuid


# ============================================================================
# Enums
# ============================================================================

class WorkflowStatus(str, Enum):
    """Workflow lifecycle states"""
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    ARCHIVED = "ARCHIVED"


class AuditLevel(str, Enum):
    """Audit logging granularity"""
    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    FULL = "FULL"
    FORENSIC = "FORENSIC"


class RiskLevel(str, Enum):
    """Risk classification for agents and capabilities"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class StepType(str, Enum):
    """Type of workflow step"""
    ACTION = "ACTION"
    HUMAN_APPROVAL = "HUMAN_APPROVAL"
    CONDITION = "CONDITION"
    PARALLEL = "PARALLEL"
    COMPENSATION = "COMPENSATION"


# ============================================================================
# Core Models
# ============================================================================

class PolicyRule(BaseModel):
    """A single policy rule for workflow execution"""
    rule_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_name: str
    allowed_capabilities: List[str] = Field(default_factory=list)
    denied_capabilities: List[str] = Field(default_factory=list)
    requires_approval_for: List[str] = Field(default_factory=list)
    allowed_environments: List[str] = Field(default_factory=lambda: ["dev", "staging", "prod"])
    max_retries: int = 3
    timeout_seconds: int = 300


class CompensationStep(BaseModel):
    """Defines how to undo/rollback a step"""
    step_name: str
    capability_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None


class WorkflowStep(BaseModel):
    """A single step in a workflow"""
    name: str
    step_type: StepType = StepType.ACTION
    agent_name: str
    capability_name: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    compensation: Optional[CompensationStep] = None
    approval_config: Optional[Dict[str, Any]] = None
    max_retries: int = 3
    timeout_seconds: int = 300
    description: Optional[str] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM


class WorkflowMetadata(BaseModel):
    """Governance and audit metadata for a workflow"""
    workflow_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    owner: str
    business_unit: Optional[str] = None
    cost_center: Optional[str] = None
    compliance_tags: List[str] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    audit_level: AuditLevel = AuditLevel.STANDARD
    retention_days: int = 90
    environment: str = "dev"
    triggered_by: Optional[str] = None
    # Pack context (for pack-aware execution)
    pack_id: Optional[str] = None  # Stable pack identifier (preferred)
    pack_name: Optional[str] = None  # Pack name (for backward compatibility)
    pack_version: Optional[str] = None  # Pack version


class WorkflowSpec(BaseModel):
    """The complete specification for a transactional multi-agent workflow"""
    name: str
    version: str = "1.0.0"
    description: str
    steps: List[WorkflowStep]
    initial_state: Dict[str, Any] = Field(default_factory=dict)
    metadata: WorkflowMetadata
    policy: List[PolicyRule] = Field(default_factory=list)
    global_compensation_steps: List[CompensationStep] = Field(default_factory=list)
    max_execution_time_seconds: int = 3600
    enable_auto_rollback: bool = True


def validate_workflow_spec(spec: WorkflowSpec) -> List[str]:
    """Validate a workflow specification for common errors"""
    errors = []
    step_names = {step.name for step in spec.steps}
    
    for step in spec.steps:
        for dep in step.depends_on:
            if dep not in step_names:
                errors.append(f"Step '{step.name}' depends on unknown step '{dep}'")
    
    return errors
