"""
AI-First Runtime v3.0 - Capability Registry Schema v1

Capability Schema with Risk & Governance Support.

This schema acts as the data source for the Policy Engine, providing:
- Risk Level classification
- Side effects reversibility
- Compensation support

Principle #3: All Side-Effects Must Be Compensable
Principle #11: Capabilities are Atomic
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class RiskLevel(Enum):
    """
    Risk level classification for capabilities.
    
    Used by Policy Engine for risk-based escalation.
    """
    LOW = "LOW"           # Read-only, no side effects
    MEDIUM = "MEDIUM"     # Reversible side effects
    HIGH = "HIGH"         # Irreversible side effects (requires approval)
    CRITICAL = "CRITICAL" # Dangerous operations (e.g., payment, deletion)


class OperationType(Enum):
    """Operation type classification"""
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    EXECUTE = "EXECUTE"
    NETWORK = "NETWORK"


class SideEffects(BaseModel):
    """
    Side effects metadata.
    
    Principle #3: All Side-Effects Must Be Compensable
    """
    reversible: bool = Field(
        ...,
        description="Whether the side effect can be reversed (undone)"
    )
    
    scope: str = Field(
        default="local",
        description="Scope of side effects: local, network, external"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of side effects"
    )


class Compensation(BaseModel):
    """
    Compensation (undo) metadata.
    
    Principle #3: All Side-Effects Must Be Compensable
    """
    supported: bool = Field(
        ...,
        description="Whether compensation (undo) is supported"
    )
    
    strategy: Optional[str] = Field(
        default=None,
        description="Compensation strategy: automatic, manual, none"
    )
    
    capability_id: Optional[str] = Field(
        default=None,
        description="ID of the compensation capability (if automatic)"
    )


class Risk(BaseModel):
    """
    Risk metadata for Policy Engine.
    
    Used for risk-based escalation and policy enforcement.
    """
    level: RiskLevel = Field(
        ...,
        description="Risk level: LOW, MEDIUM, HIGH, CRITICAL"
    )
    
    justification: Optional[str] = Field(
        default=None,
        description="Justification for the risk level"
    )
    
    requires_approval: bool = Field(
        default=False,
        description="Whether this capability always requires human approval"
    )


class CapabilityParameter(BaseModel):
    """Capability parameter definition"""
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Optional[Any] = None


class CapabilityMetadata(BaseModel):
    """Capability metadata"""
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    deprecated: bool = False


class CapabilitySpec(BaseModel):
    """
    Capability Registry Schema v1
    
    Complete specification for a capability with risk & governance support.
    
    MANDATORY FIELDS (Week 6):
    - risk.level: RiskLevel
    - side_effects.reversible: bool
    - compensation.supported: bool
    """
    
    # Core identification
    id: str = Field(
        ...,
        description="Unique capability ID (e.g., 'io.fs.read_file')"
    )
    
    name: str = Field(
        ...,
        description="Human-readable name"
    )
    
    description: str = Field(
        ...,
        description="Detailed description of what this capability does"
    )
    
    # Operation classification
    operation_type: OperationType = Field(
        ...,
        description="Type of operation: READ, WRITE, DELETE, EXECUTE, NETWORK"
    )
    
    # MANDATORY: Risk & Governance (Week 6)
    risk: Risk = Field(
        ...,
        description="Risk metadata for Policy Engine"
    )
    
    side_effects: SideEffects = Field(
        ...,
        description="Side effects metadata"
    )
    
    compensation: Compensation = Field(
        ...,
        description="Compensation (undo) metadata"
    )
    
    # Parameters
    parameters: List[CapabilityParameter] = Field(
        default_factory=list,
        description="Input parameters"
    )
    
    # Return value
    returns: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Return value schema"
    )
    
    # Metadata
    metadata: CapabilityMetadata = Field(
        default_factory=CapabilityMetadata,
        description="Additional metadata"
    )
    
    # Handler
    handler: Optional[str] = Field(
        default=None,
        description="Python handler function path (e.g., 'module.function')"
    )
    
    def model_post_init(self, __context) -> None:
        """
        Risk Consistency Check (Week 6 Acceptance Criteria)
        
        Validation rules:
        1. If side_effects.reversible == False -> risk.level must be HIGH or CRITICAL
        2. If operation_type == DELETE -> risk.level must be at least HIGH
        3. If compensation.supported == False and side_effects.reversible == False -> CRITICAL
        """
        # Rule 1: Irreversible side effects must be HIGH+ risk
        if not self.side_effects.reversible:
            if self.risk.level not in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                raise ValueError(
                    f"Risk Consistency Check Failed: "
                    f"Irreversible side effects (reversible=false) require "
                    f"risk level HIGH or CRITICAL, got {self.risk.level.value}"
                )
        
        # Rule 2: DELETE operations must be HIGH+ risk
        if self.operation_type == OperationType.DELETE:
            if self.risk.level not in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                raise ValueError(
                    f"Risk Consistency Check Failed: "
                    f"DELETE operations require risk level HIGH or CRITICAL, "
                    f"got {self.risk.level.value}"
                )
        
        # Rule 3: No compensation + irreversible = CRITICAL
        if not self.compensation.supported and not self.side_effects.reversible:
            if self.risk.level != RiskLevel.CRITICAL:
                raise ValueError(
                    f"Risk Consistency Check Failed: "
                    f"No compensation support + irreversible side effects "
                    f"require CRITICAL risk level, got {self.risk.level.value}"
                )
    
    def get_risk_level(self) -> RiskLevel:
        """Get risk level (convenience method for Policy Engine)"""
        return self.risk.level
    
    def is_reversible(self) -> bool:
        """Check if side effects are reversible"""
        return self.side_effects.reversible
    
    def supports_compensation(self) -> bool:
        """Check if compensation is supported"""
        return self.compensation.supported
    
    def requires_approval(self) -> bool:
        """Check if this capability always requires approval"""
        return self.risk.requires_approval


# Helper functions for common capability patterns

def create_read_capability(
    capability_id: str,
    name: str,
    description: str,
    parameters: List[CapabilityParameter],
    handler: Optional[str] = None
) -> CapabilitySpec:
    """
    Create a READ capability with LOW risk (default pattern).
    
    READ capabilities:
    - No side effects (reversible=True by convention)
    - Compensation not needed (supported=False)
    - LOW risk
    """
    return CapabilitySpec(
        id=capability_id,
        name=name,
        description=description,
        operation_type=OperationType.READ,
        risk=Risk(
            level=RiskLevel.LOW,
            justification="Read-only operation with no side effects"
        ),
        side_effects=SideEffects(
            reversible=True,
            scope="local",
            description="No side effects"
        ),
        compensation=Compensation(
            supported=False,
            strategy="none"
        ),
        parameters=parameters,
        handler=handler
    )


def create_write_capability(
    capability_id: str,
    name: str,
    description: str,
    parameters: List[CapabilityParameter],
    reversible: bool = True,
    compensation_capability_id: Optional[str] = None,
    handler: Optional[str] = None
) -> CapabilitySpec:
    """
    Create a WRITE capability with appropriate risk level.
    
    WRITE capabilities:
    - If reversible=True -> MEDIUM risk, compensation supported
    - If reversible=False -> HIGH risk, compensation MUST be supported (to avoid CRITICAL)
    """
    risk_level = RiskLevel.MEDIUM if reversible else RiskLevel.HIGH
    
    return CapabilitySpec(
        id=capability_id,
        name=name,
        description=description,
        operation_type=OperationType.WRITE,
        risk=Risk(
            level=risk_level,
            justification=f"Write operation ({'reversible' if reversible else 'irreversible'})"
        ),
        side_effects=SideEffects(
            reversible=reversible,
            scope="local",
            description="Modifies filesystem or state"
        ),
        compensation=Compensation(
            supported=True,  # Always supported to avoid CRITICAL requirement
            strategy="automatic" if reversible else "manual",
            capability_id=compensation_capability_id
        ),
        parameters=parameters,
        handler=handler
    )


def create_delete_capability(
    capability_id: str,
    name: str,
    description: str,
    parameters: List[CapabilityParameter],
    compensation_capability_id: Optional[str] = None,
    handler: Optional[str] = None
) -> CapabilitySpec:
    """
    Create a DELETE capability with HIGH risk (always).
    
    DELETE capabilities:
    - Always HIGH risk (may be escalated to CRITICAL by policy)
    - Side effects are typically irreversible
    - Compensation MUST be supported (to avoid CRITICAL requirement)
    """
    return CapabilitySpec(
        id=capability_id,
        name=name,
        description=description,
        operation_type=OperationType.DELETE,
        risk=Risk(
            level=RiskLevel.HIGH,
            justification="DELETE operations are inherently high-risk",
            requires_approval=True  # Always require approval
        ),
        side_effects=SideEffects(
            reversible=False,
            scope="local",
            description="Permanently deletes data"
        ),
        compensation=Compensation(
            supported=True,  # Always supported to avoid CRITICAL requirement
            strategy="automatic" if compensation_capability_id else "manual",
            capability_id=compensation_capability_id
        ),
        parameters=parameters,
        handler=handler
    )
