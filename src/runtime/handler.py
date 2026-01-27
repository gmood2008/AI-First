"""
Action Handler base class and utilities.

This module defines the abstract interface that all capability implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
import yaml
from pathlib import Path

from .types import ActionOutput


class ActionHandler(ABC):
    """
    Abstract base class for all capability implementations.
    
    Each capability in the StdLib must have a corresponding ActionHandler
    that implements the actual execution logic.
    
    The handler is responsible for:
    1. Validating input parameters against the spec
    2. Executing the capability logic
    3. Returning outputs in the format defined by the spec
    4. Providing undo information if applicable
    """
    
    def __init__(self, spec_dict: Dict[str, Any]):
        """
        Initialize handler with capability specification.
        
        Args:
            spec_dict: Parsed YAML specification as dictionary
        """
        self.spec = spec_dict
        self.capability_id = spec_dict["meta"]["id"]
        self.version = spec_dict["meta"]["version"]
        self.contracts = spec_dict["contracts"]
        self.behavior = spec_dict["behavior"]
        self.interface = spec_dict["interface"]
    
    @abstractmethod
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        """
        Execute the capability with given parameters.
        
        This is the core method that must be implemented by all handlers.
        
        Args:
            params: Input parameters matching spec.interface.inputs
            context: ExecutionContext providing environment information
        
        Returns:
            ActionOutput containing:
            - result: Dictionary of outputs matching spec.interface.outputs
            - undo_closure: Optional function to reverse the operation
            - description: Human-readable description of what was done
        
        Raises:
            ValidationError: If parameters don't match spec
            SecurityError: If operation violates security constraints
            Any other exception: Execution failure
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> None:
        """
        Validate parameters against spec.interface.inputs.
        
        Args:
            params: Parameters to validate
        
        Raises:
            ValidationError: If validation fails
        """
        inputs_spec = self.interface["inputs"]
        
        for param_name, param_spec in inputs_spec.items():
            required = param_spec.get("required", True)
            
            if required and param_name not in params:
                raise ValueError(f"Required parameter '{param_name}' missing")
            
            if param_name in params:
                value = params[param_name]
                expected_type = param_spec["type"]
                
                # Basic type checking
                if not self._check_type(value, expected_type):
                    raise ValueError(
                        f"Parameter '{param_name}' has wrong type. "
                        f"Expected {expected_type}, got {type(value).__name__}"
                    )
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """
        Check if value matches expected type.
        
        Args:
            value: Value to check
            expected_type: Expected type name (string, integer, etc.)
        
        Returns:
            True if type matches
        """
        type_map = {
            "string": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None),
        }
        
        if expected_type == "enum":
            # For enum, just check if it's a string
            return isinstance(value, str)
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, skip check
        
        return isinstance(value, expected_python_type)
    
    def requires_confirmation(self) -> bool:
        """
        Check if this capability requires user confirmation.
        
        Returns:
            True if confirmation is required
        """
        return self.contracts.get("requires_confirmation", False)
    
    def get_side_effects(self) -> list:
        """
        Get list of side effects this capability produces.
        
        Returns:
            List of side effect types
        """
        return self.contracts.get("side_effects", [])
    
    def get_undo_strategy(self) -> str:
        """
        Get the undo strategy description.
        
        Returns:
            Undo strategy string from spec
        """
        return self.behavior.get("undo_strategy", "")
    
    def is_idempotent(self) -> bool:
        """
        Check if this capability is idempotent.
        
        Returns:
            True if repeated execution produces same result
        """
        return self.contracts.get("idempotent", False)
    
    def get_timeout_seconds(self) -> int:
        """
        Get execution timeout in seconds.
        
        Returns:
            Timeout value, or 30 seconds default
        """
        return self.contracts.get("timeout_seconds", 30)
    
    def get_cost_model(self) -> str:
        """
        Get the cost model for this capability.
        
        Returns:
            Cost model string (free, low_io, etc.)
        """
        return self.behavior.get("cost_model", "free")
    
    def get_description(self) -> str:
        """
        Get human-readable description of this capability.
        
        Returns:
            Description string
        """
        return self.spec["meta"].get("description", "")
    
    def to_info_dict(self) -> Dict[str, Any]:
        """
        Convert handler information to dictionary.
        
        Returns:
            Dictionary with capability metadata
        """
        return {
            "id": self.capability_id,
            "version": self.version,
            "description": self.get_description(),
            "author": self.spec["meta"].get("author", "Unknown"),
            "requires_confirmation": self.requires_confirmation(),
            "side_effects": self.get_side_effects(),
            "undo_strategy": self.get_undo_strategy(),
            "cost_model": self.get_cost_model(),
            "idempotent": self.is_idempotent(),
            "timeout_seconds": self.get_timeout_seconds(),
        }


def load_spec_from_yaml(yaml_path: Path) -> Dict[str, Any]:
    """
    Load capability specification from YAML file.
    
    Args:
        yaml_path: Path to YAML file
    
    Returns:
        Parsed specification as dictionary
    """
    with open(yaml_path, "r") as f:
        return yaml.safe_load(f)


def create_handler_from_yaml(yaml_path: Path, handler_class: type) -> ActionHandler:
    """
    Create handler instance from YAML specification.
    
    Args:
        yaml_path: Path to YAML specification
        handler_class: Handler class to instantiate
    
    Returns:
        Initialized handler instance
    """
    spec_dict = load_spec_from_yaml(yaml_path)
    return handler_class(spec_dict)
