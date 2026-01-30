from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from src.specs.v3.capability_schema import RiskLevel


class ExternalToolType(str, Enum):
    SIDECAR_HTTP = "SIDECAR_HTTP"
    SUBPROCESS = "SUBPROCESS"
    CONTAINER = "CONTAINER"


class ExternalToolRef(BaseModel):
    source: str = Field(..., description="External tool source, e.g. 'github' or 'local'")
    repo: Optional[str] = Field(default=None, description="Repository URL or identifier")
    type: ExternalToolType = Field(..., description="How the tool is invoked")


class AdapterContract(BaseModel):
    input_schema: Dict[str, Any] = Field(..., description="JSON-schema-like input schema")
    output_schema: Dict[str, Any] = Field(..., description="JSON-schema-like output schema")


class ExecutionConstraints(BaseModel):
    timeout_seconds: int = Field(default=30, ge=1, le=3600)
    allowed_domains: List[str] = Field(default_factory=list)


class AdapterRiskProfile(BaseModel):
    max_risk: RiskLevel = Field(..., description="Risk classification")
    requires_human_approval: bool = Field(default=False)


class AdapterGovernance(BaseModel):
    approval_roles: List[str] = Field(default_factory=list)
    audit_level: str = Field(default="DETAILED")


class ExternalCapabilityAdapterSpec(BaseModel):
    name: str = Field(..., description="Adapter capability name")
    version: str = Field(..., description="Semantic version (x.y.z)")

    external_tool: ExternalToolRef
    adapter_contract: AdapterContract
    execution_constraints: ExecutionConstraints = Field(default_factory=ExecutionConstraints)
    risk_profile: AdapterRiskProfile
    governance: AdapterGovernance = Field(default_factory=AdapterGovernance)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("version must be x.y.z")
        for p in parts:
            if not p.isdigit():
                raise ValueError("version components must be integers")
        return v
