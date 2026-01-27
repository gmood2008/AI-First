"""
Data structures for Smart Importer.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal


class SourceType(Enum):
    """Type of import source"""
    PYTHON_FILE = "python_file"
    PYTHON_CODE = "python_code"
    OPENAPI_SPEC = "openapi_spec"
    URL = "url"


SideEffectType = Literal[
    "filesystem_read",
    "filesystem_write",
    "filesystem_delete",
    "network_read",
    "network_write",
    "system_exec",
    "state_mutation"
]

CostModel = Literal["free", "low_io", "high_io", "network", "compute"]


@dataclass
class ParameterInfo:
    """Information about a function parameter"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    sensitive: bool = False


@dataclass
class ReturnInfo:
    """Information about a return value"""
    name: str
    type: str
    description: str


@dataclass
class FunctionInfo:
    """Information extracted from Python function"""
    name: str
    docstring: str
    parameters: List[ParameterInfo]
    return_type: str
    side_effects: List[SideEffectType]
    source_code: str
    module_name: Optional[str] = None


@dataclass
class EndpointInfo:
    """Information extracted from OpenAPI endpoint"""
    path: str
    method: str
    summary: str
    description: str
    parameters: List[ParameterInfo]
    responses: Dict[str, Any]
    side_effects: List[SideEffectType]
    tags: List[str] = field(default_factory=list)


@dataclass
class MetaInfo:
    """Capability metadata"""
    id: str
    version: str
    author: str
    description: str


@dataclass
class Contracts:
    """Capability contracts"""
    side_effects: List[SideEffectType]
    requires_confirmation: bool
    idempotent: bool
    timeout_seconds: int = 30


@dataclass
class Behavior:
    """Capability behavior"""
    undo_strategy: str
    cost_model: CostModel


@dataclass
class InterfaceParam:
    """Interface parameter definition"""
    type: str
    description: str
    required: bool = True
    sensitive: bool = False
    default: Optional[Any] = None


@dataclass
class InterfaceOutput:
    """Interface output definition"""
    type: str
    description: str


@dataclass
class Interface:
    """Capability interface"""
    inputs: Dict[str, InterfaceParam]
    outputs: Dict[str, InterfaceOutput]


@dataclass
class CapabilitySpec:
    """Complete capability specification"""
    meta: MetaInfo
    contracts: Contracts
    behavior: Behavior
    interface: Interface
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization"""
        return {
            "meta": {
                "id": self.meta.id,
                "version": self.meta.version,
                "author": self.meta.author,
                "description": self.meta.description,
            },
            "contracts": {
                "side_effects": self.contracts.side_effects,
                "requires_confirmation": self.contracts.requires_confirmation,
                "idempotent": self.contracts.idempotent,
                "timeout_seconds": self.contracts.timeout_seconds,
            },
            "behavior": {
                "undo_strategy": self.behavior.undo_strategy,
                "cost_model": self.behavior.cost_model,
            },
            "interface": {
                "inputs": {
                    name: {
                        "type": param.type,
                        "description": param.description,
                        "required": param.required,
                        **({"sensitive": True} if param.sensitive else {}),
                        **({"default": param.default} if param.default is not None else {}),
                    }
                    for name, param in self.interface.inputs.items()
                },
                "outputs": {
                    name: {
                        "type": output.type,
                        "description": output.description,
                    }
                    for name, output in self.interface.outputs.items()
                },
            },
        }


@dataclass
class ValidationResult:
    """Result of spec validation"""
    valid: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
