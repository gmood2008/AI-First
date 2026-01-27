"""
AI-First Runtime v3.1 - Capability Pack Specification

A Capability Pack is a governed composition of capabilities and workflows
that together solve a domain-level problem.

Core Principles:
1. Pack is a first-class governance entity
2. Proposal-only registration
3. Pack-level risk MUST dominate included capability risks
4. Governance power lives outside the UI
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from .v3.capability_schema import RiskLevel


# ---------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------

class PackState(str, Enum):
    """Lifecycle states for a capability pack"""
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    DEPRECATED = "DEPRECATED"


# ---------------------------------------------------------------------
# Risk & Governance
# ---------------------------------------------------------------------

class AuditLevel(str, Enum):
    """Audit and traceability depth"""
    BASIC = "BASIC"
    DETAILED = "DETAILED"
    FORENSIC = "FORENSIC"


class PackRiskProfile(BaseModel):
    """
    Risk profile for the entire pack.

    This defines factual risk constraints, NOT organizational process.
    """
    max_risk: RiskLevel = Field(
        ...,
        description="Maximum risk level allowed for any capability in this pack"
    )

    requires_human_approval: bool = Field(
        default=False,
        description="Whether execution of this pack requires explicit human approval"
    )

    auto_rollback_on_failure: bool = Field(
        default=True,
        description="Whether to rollback the entire pack execution on any failure"
    )


class PackGovernance(BaseModel):
    """
    Governance metadata defining HOW humans oversee this pack,
    not WHETHER they are required.
    """
    approval_roles: List[str] = Field(
        default_factory=list,
        description="Roles allowed to approve proposals related to this pack"
    )

    audit_level: AuditLevel = Field(
        default=AuditLevel.DETAILED,
        description="Audit logging level for this pack"
    )


# ---------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------

class PackIncludes(BaseModel):
    """
    References to included system components.

    All references must exist in their respective registries.
    """
    capabilities: List[str] = Field(
        default_factory=list,
        description="Capability IDs included in this pack"
    )

    workflows: List[str] = Field(
        default_factory=list,
        description="Workflow IDs included in this pack"
    )


# ---------------------------------------------------------------------
# Capability Pack Specification
# ---------------------------------------------------------------------

class CapabilityPackSpec(BaseModel):
    """
    Capability Pack Specification (v3.1)

    A Pack is a governed, versioned, and auditable composition
    of capabilities and workflows.
    """

    # -----------------------------------------------------------------
    # Identity (Stable)
    # -----------------------------------------------------------------

    pack_id: str = Field(
        ...,
        description="Stable global identifier (e.g., 'pack.financial.analyst')"
    )

    name: str = Field(
        ...,
        description="Human-readable name (e.g., 'financial-analyst')"
    )

    version: str = Field(
        ...,
        description="Semantic version (e.g., '1.0.0')"
    )

    # -----------------------------------------------------------------
    # Description
    # -----------------------------------------------------------------

    description: str = Field(
        ...,
        description="What this pack does"
    )

    responsibility: Optional[str] = Field(
        default=None,
        description="Explicit responsibility boundary (what this pack is / is not responsible for)"
    )

    # -----------------------------------------------------------------
    # Composition
    # -----------------------------------------------------------------

    includes: PackIncludes = Field(
        ...,
        description="Referenced capabilities and workflows"
    )

    # -----------------------------------------------------------------
    # Risk & Governance
    # -----------------------------------------------------------------

    risk_profile: PackRiskProfile = Field(
        ...,
        description="Pack-level risk constraints"
    )

    governance: PackGovernance = Field(
        default_factory=PackGovernance,
        description="Human governance metadata"
    )

    # -----------------------------------------------------------------
    # Metadata
    # -----------------------------------------------------------------

    author: str = Field(
        default="unknown",
        description="Pack author or owning team"
    )

    tags: List[str] = Field(
        default_factory=list,
        description="Classification tags (e.g., finance, compliance)"
    )

    created_at: Optional[datetime] = Field(
        default=None,
        description="Creation timestamp"
    )

    state: PackState = Field(
        default=PackState.PROPOSED,
        description="Current lifecycle state"
    )

    # -----------------------------------------------------------------
    # Validators
    # -----------------------------------------------------------------

    @field_validator("pack_id")
    @classmethod
    def validate_pack_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("pack_id cannot be empty")
        if " " in v:
            raise ValueError("pack_id must not contain spaces")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Pack name cannot be empty")
        if " " in v:
            raise ValueError("Pack name cannot contain spaces")
        return v.strip()

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("Version must follow semantic versioning (x.y.z)")
        try:
            int(parts[0])
            int(parts[1])
            int(parts[2])
        except ValueError:
            raise ValueError("Version components must be integers")
        return v

    # -----------------------------------------------------------------
    # Lifecycle hooks
    # -----------------------------------------------------------------

    def model_post_init(self, __context) -> None:
        if self.created_at is None:
            self.created_at = datetime.utcnow()

    # -----------------------------------------------------------------
    # Serialization
    # -----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityPackSpec":
        return cls.model_validate(data)
