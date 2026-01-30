"""
Skill Facade Spec v1.0 - Human/LLM-friendly capability entry layer.

A Skill Facade is a semantic entry description that routes natural language
requests to Capability / Workflow / Pack. It does NOT execute, hold risk,
approve, or define permissions.

Design:
- triggers = semantic index for LLM routing / UI / CLI (not execution prompt)
- routes = explicit, governable primary/fallback to workflow or pack
- constraints = declaration only; Runtime performs checks when resolving
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Route types (ref = workflow name or pack name/id)
# ---------------------------------------------------------------------------

class RouteType(str, Enum):
    WORKFLOW = "workflow"
    PACK = "pack"


class RouteTarget(BaseModel):
    """Single route target: workflow or pack reference."""
    type: RouteType = Field(..., description="workflow or pack")
    ref: str = Field(..., description="Workflow name or pack id/name")


# ---------------------------------------------------------------------------
# Routes (primary + optional fallback)
# ---------------------------------------------------------------------------

class FacadeRoutes(BaseModel):
    """Routing from facade to capability layer. No capability IDs here."""
    primary: RouteTarget = Field(..., description="Preferred target (workflow or pack)")
    fallback: Optional[RouteTarget] = Field(default=None, description="Fallback target")


# ---------------------------------------------------------------------------
# Constraints (declaration only; Runtime enforces)
# ---------------------------------------------------------------------------

class FacadeConstraints(BaseModel):
    """Declared constraints. Facade does not enforce; Runtime checks when resolving."""
    requires_pack_active: bool = Field(default=True, description="Execution requires pack in ACTIVE state")
    supported_environments: List[str] = Field(
        default_factory=lambda: ["prod", "staging"],
        description="Environments where this facade is valid"
    )


# ---------------------------------------------------------------------------
# Examples (for retrieval/display only)
# ---------------------------------------------------------------------------

class FacadeExample(BaseModel):
    """Single example: user utterance (and optional assistant)."""
    user: str = Field(..., description="Example user / LLM trigger phrase")
    assistant: Optional[str] = Field(default=None, description="Optional expected response description")


# ---------------------------------------------------------------------------
# Metadata (retrieval and display only)
# ---------------------------------------------------------------------------

class FacadeMetadata(BaseModel):
    """Metadata for discovery and compatibility. No governance."""
    category: Optional[str] = Field(default=None, description="e.g. document-processing")
    compatible_with: List[str] = Field(
        default_factory=lambda: ["claude-skill", "copilot-skill"],
        description="Compatible skill surfaces"
    )
    owner: str = Field(default="ai-first", description="Owning team or system")
    maturity: str = Field(default="stable", description="e.g. stable, beta")


# ---------------------------------------------------------------------------
# Skill Facade Spec v1.0
# ---------------------------------------------------------------------------

class SkillFacadeSpec(BaseModel):
    """
    Skill Facade Specification v1.0.

    Human/LLM-friendly entry layer. Routes to Workflow / Pack only.
    No execution, no risk, no approval, no direct Capability ID.
    """

    name: str = Field(..., description="Facade name (e.g. 'pdf', 'financial-analyst')")
    version: str = Field(..., description="Semantic version (e.g. '1.0.0')")
    description: str = Field(..., description="What this facade offers (natural language)")

    triggers: List[str] = Field(
        ...,
        min_length=1,
        description="Semantic trigger phrases for routing (not execution prompt)"
    )
    examples: List[FacadeExample] = Field(
        default_factory=list,
        description="Example user utterances for retrieval/display"
    )

    routes: FacadeRoutes = Field(..., description="Primary and optional fallback route")
    constraints: FacadeConstraints = Field(
        default_factory=FacadeConstraints,
        description="Declared constraints; Runtime enforces"
    )
    metadata: FacadeMetadata = Field(
        default_factory=FacadeMetadata,
        description="Category, compatibility, owner, maturity"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError("version must be x.y.z")
        for p in parts:
            if not p.isdigit():
                raise ValueError("version components must be integers")
        return v

    # -----------------------------------------------------------------------
    # Serialization (YAML/JSON; no execution logic)
    # -----------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillFacadeSpec":
        return cls.model_validate(data)

    @classmethod
    def from_yaml(cls, content: str) -> "SkillFacadeSpec":
        import yaml
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError("YAML must parse to a dict")
        return cls.from_dict(data)

    def to_yaml(self) -> str:
        import yaml
        return yaml.safe_dump(self.to_dict(), default_flow_style=False, allow_unicode=True)
