"""
Skill Converter - Convert third-party capabilities to AI-First format

Supports:
- Claude Skills
- OpenAI Functions
- Generic HTTP APIs
- LangChain Tools (future)
"""

from typing import Dict, Any, Optional
from pathlib import Path
import yaml

from specs.v3.capability_schema import (
    CapabilitySpec,
    CapabilityMetadata,
    Risk,
    RiskLevel,
    SideEffects,
    Compensation,
    OperationType,
    CapabilityParameter,
)


class SkillConverter:
    """
    Convert third-party capabilities to AI-First capability specifications.
    """
    
    def __init__(self):
        """Initialize skill converter"""
        pass
    
    def convert_claude_skill(
        self,
        skill_definition: Dict[str, Any],
        capability_id: str,
        adapter_config: Optional[Dict[str, Any]] = None
    ) -> CapabilitySpec:
        """
        Convert Claude Skill definition to AI-First capability spec.
        
        Args:
            skill_definition: Claude Skill JSON definition
            capability_id: Desired AI-First capability ID
            adapter_config: Optional adapter configuration
        
        Returns:
            CapabilitySpec object
        """
        # Extract information from Claude Skill definition
        skill_name = skill_definition.get("name", capability_id)
        skill_description = skill_definition.get("description", "")
        skill_inputs = skill_definition.get("input_schema", {}).get("properties", {})
        skill_outputs = skill_definition.get("output_schema", {}).get("properties", {})
        
        # Convert inputs to CapabilityParameter list
        parameters = []
        for param_name, param_schema in skill_inputs.items():
            param_type = param_schema.get("type", "string")
            parameters.append(CapabilityParameter(
                name=param_name,
                type=param_type,
                description=param_schema.get("description", f"{param_name} parameter"),
                required=param_name in skill_inputs.get("required", []),
                default=param_schema.get("default")
            ))
        
        # Convert outputs to returns schema
        returns = {
            "type": "object",
            "properties": {}
        }
        for output_name, output_schema in skill_outputs.items():
            returns["properties"][output_name] = {
                "type": output_schema.get("type", "string"),
                "description": output_schema.get("description", f"{output_name} value")
            }
        
        # Determine operation type and risk
        operation_type = OperationType.NETWORK  # External API calls are network operations
        # External capabilities with irreversible side effects and no compensation
        # require CRITICAL risk level per validation rules
        risk_level = RiskLevel.CRITICAL  # External capabilities default to CRITICAL
        
        # Create spec
        spec = CapabilitySpec(
            id=capability_id,
            name=skill_name,
            description=skill_description or f"Claude Skill: {skill_name}",
            operation_type=operation_type,
            risk=Risk(
                level=risk_level,
                justification="External API call via Claude Skill (irreversible, no compensation)",
                requires_approval=True  # CRITICAL always requires approval
            ),
            side_effects=SideEffects(
                reversible=False,  # External capabilities typically not reversible
                scope="external",
                description="External API call"
            ),
            compensation=Compensation(
                supported=False,  # External capabilities typically don't support undo
                strategy=None,
                capability_id=None
            ),
            parameters=parameters,
            returns=returns,
            metadata=CapabilityMetadata(
                version="1.0.0",
                author="SkillConverter",
                tags=["external", "claude_skill"]
            ),
            handler=f"runtime.adapters.claude_skill.ClaudeSkillAdapter"
        )
        
        # Note: adapter_config is stored in the YAML file separately,
        # not in the CapabilitySpec object
        
        return spec
    
    def convert_openai_function(
        self,
        function_definition: Dict[str, Any],
        capability_id: str,
        adapter_config: Optional[Dict[str, Any]] = None
    ) -> CapabilitySpec:
        """
        Convert OpenAI Function definition to AI-First capability spec.
        
        Args:
            function_definition: OpenAI Function JSON definition
            capability_id: Desired AI-First capability ID
            adapter_config: Optional adapter configuration
        
        Returns:
            CapabilitySpec object
        """
        # Extract information
        func_name = function_definition.get("name", capability_id)
        func_description = function_definition.get("description", "")
        func_parameters = function_definition.get("parameters", {}).get("properties", {})
        func_required = function_definition.get("parameters", {}).get("required", [])
        
        # Convert parameters
        parameters = []
        for param_name, param_schema in func_parameters.items():
            param_type = param_schema.get("type", "string")
            parameters.append(CapabilityParameter(
                name=param_name,
                type=param_type,
                description=param_schema.get("description", f"{param_name} parameter"),
                required=param_name in func_required,
                default=None
            ))
        
        # Create spec
        spec = CapabilitySpec(
            id=capability_id,
            name=func_name,
            description=func_description or f"OpenAI Function: {func_name}",
            operation_type=OperationType.NETWORK,
            risk=Risk(
                level=RiskLevel.CRITICAL,
                justification="External API call via OpenAI Function (irreversible, no compensation)",
                requires_approval=True
            ),
            side_effects=SideEffects(
                reversible=False,
                scope="external",
                description="External API call"
            ),
            compensation=Compensation(
                supported=False,
                strategy=None,
                capability_id=None
            ),
            parameters=parameters,
            returns={
                "type": "object",
                "properties": {
                    "result": {
                        "type": "string",
                        "description": "Function execution result"
                    }
                }
            },
            metadata=CapabilityMetadata(
                version="1.0.0",
                author="SkillConverter",
                tags=["external", "openai_function"]
            ),
            handler=f"runtime.adapters.openai_function.OpenAIFunctionAdapter"
        )
        
        return spec
    
    def convert_http_api(
        self,
        api_definition: Dict[str, Any],
        capability_id: str,
        adapter_config: Optional[Dict[str, Any]] = None
    ) -> CapabilitySpec:
        """
        Convert HTTP API definition to AI-First capability spec.
        
        Args:
            api_definition: HTTP API definition (OpenAPI-like)
            capability_id: Desired AI-First capability ID
            adapter_config: Optional adapter configuration
        
        Returns:
            CapabilitySpec object
        """
        # Extract information
        api_name = api_definition.get("name", capability_id)
        api_description = api_definition.get("description", "")
        api_method = api_definition.get("method", "POST")
        api_params = api_definition.get("parameters", {})
        
        # Convert parameters
        parameters = []
        for param_name, param_info in api_params.items():
            param_type = param_info.get("type", "string")
            parameters.append(CapabilityParameter(
                name=param_name,
                type=param_type,
                description=param_info.get("description", f"{param_name} parameter"),
                required=param_info.get("required", False),
                default=param_info.get("default")
            ))
        
        # Determine risk based on method
        # External capabilities are typically irreversible with no compensation
        # Per validation rules: irreversible + no compensation = CRITICAL
        if api_method in ["DELETE"]:
            risk_level = RiskLevel.CRITICAL  # DELETE operations are critical
        else:
            risk_level = RiskLevel.CRITICAL  # All external APIs are CRITICAL (irreversible, no compensation)
        
        # Create spec
        spec = CapabilitySpec(
            id=capability_id,
            name=api_name,
            description=api_description or f"HTTP API: {api_method} {api_definition.get('endpoint', '')}",
            operation_type=OperationType.NETWORK,
            risk=Risk(
                level=risk_level,
                justification=f"HTTP {api_method} request to external API (irreversible, no compensation)",
                requires_approval=True  # CRITICAL always requires approval
            ),
            side_effects=SideEffects(
                reversible=False,
                scope="network",
                description=f"HTTP {api_method} request"
            ),
            compensation=Compensation(
                supported=False,
                strategy=None,
                capability_id=None
            ),
            parameters=parameters,
            returns={
                "type": "object",
                "properties": {
                    "result": {
                        "type": "string",
                        "description": "API response"
                    }
                }
            },
            metadata=CapabilityMetadata(
                version="1.0.0",
                author="SkillConverter",
                tags=["external", "http_api"]
            ),
            handler=f"runtime.adapters.http_api.HTTPAPIAdapter"
        )
        
        return spec
    
    def generate_handler_wrapper(
        self,
        spec: CapabilitySpec,
        adapter_type: str,
        adapter_config: Dict[str, Any]
    ) -> str:
        """
        Generate Handler wrapper code for external capability.
        
        Args:
            spec: CapabilitySpec
            adapter_type: Type of adapter ("claude_skill", "openai_function", "http_api")
            adapter_config: Adapter configuration
        
        Returns:
            Python code as string
        """
        capability_id = spec.id
        class_name = self._class_name_from_id(capability_id)
        
        # Generate handler code
        handler_code = f'''"""
Auto-generated handler for external capability: {capability_id}

This handler wraps the {adapter_type} adapter.
"""

from typing import Dict, Any
from runtime.handler import ActionHandler
from runtime.types import ActionOutput, ExecutionContext
from runtime.adapters import create_adapter

class {class_name}(ActionHandler):
    """
    Handler for {capability_id}
    
    Wraps external capability via {adapter_type} adapter.
    """
    
    def __init__(self, spec_dict: Dict[str, Any]):
        super().__init__(spec_dict)
        
        # Create adapter
        adapter_config = {adapter_config!r}
        self.adapter = create_adapter("{adapter_type}", adapter_config)
    
    def execute(
        self,
        params: Dict[str, Any],
        context: ExecutionContext
    ) -> ActionOutput:
        """Execute external capability via adapter"""
        # Create handler from adapter
        handler = self.adapter.create_handler(self.spec)
        
        # Execute
        return handler.execute(params, context)
'''
        
        return handler_code
    
    def _class_name_from_id(self, capability_id: str) -> str:
        """Convert capability ID to class name"""
        parts = capability_id.split(".")
        return "".join(word.capitalize() for word in parts) + "Handler"
