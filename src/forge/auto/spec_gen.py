"""
Spec Generator - Generates valid CapabilitySpec (YAML-ready) from parsed requirement.

This module converts ParsedRequirement into a complete CapabilitySpec using the v3 schema.
"""

from typing import List
import sys
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from .types import ParsedRequirement, IntentCategory, SideEffectType
from specs.v3.capability_schema import (
    CapabilitySpec,
    RiskLevel,
    OperationType,
    Risk,
    SideEffects,
    Compensation,
    CapabilityParameter,
    CapabilityMetadata
)


class SpecGenerator:
    """
    Generate CapabilitySpec from ParsedRequirement.
    
    Maps parsed requirements to the v3 capability schema with proper
    risk levels, side effects, and compensation metadata.
    """
    
    def generate(self, parsed: ParsedRequirement, capability_id: str) -> CapabilitySpec:
        """
        Generate CapabilitySpec from ParsedRequirement.
        
        Args:
            parsed: Parsed requirement
            capability_id: Desired capability ID (e.g., "net.crypto.get_price")
        
        Returns:
            Complete CapabilitySpec ready for YAML serialization
        """
        # Map intent category to operation type
        operation_type = self._map_intent_to_operation(parsed.intent_category)
        
        # Determine risk level based on side effects
        risk_level = self._determine_risk_level(parsed.side_effects, operation_type)
        
        # Determine if side effects are reversible
        reversible = self._is_reversible(parsed.side_effects, parsed.intent_category)
        
        # Determine if compensation is supported
        compensation_supported = len(parsed.side_effects) > 0 and reversible
        
        # Generate parameters from inputs
        parameters = self._generate_parameters(parsed.inputs)
        
        # Generate returns schema from outputs
        returns = self._generate_returns(parsed.outputs)
        
        # Generate capability name
        name = self._generate_name(parsed.action, parsed.target)
        
        # Generate description
        description = self._generate_description(parsed)
        
        # Generate handler path
        handler = self._generate_handler_path(capability_id)
        
        return CapabilitySpec(
            id=capability_id,
            name=name,
            description=description,
            operation_type=operation_type,
            risk=Risk(
                level=risk_level,
                justification=self._generate_risk_justification(parsed, risk_level),
                requires_approval=risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            ),
            side_effects=SideEffects(
                reversible=reversible,
                scope=self._determine_scope(parsed.side_effects),
                description=self._generate_side_effects_description(parsed.side_effects)
            ),
            compensation=Compensation(
                supported=compensation_supported,
                strategy="automatic" if compensation_supported and reversible else "manual" if compensation_supported else None,
                capability_id=None  # Can be set later if a specific undo capability exists
            ),
            parameters=parameters,
            returns=returns,
            metadata=CapabilityMetadata(
                version="1.0.0",
                author="AutoForge",
                tags=self._generate_tags(parsed)
            ),
            handler=handler
        )
    
    def _map_intent_to_operation(self, intent: IntentCategory) -> OperationType:
        """Map intent category to operation type"""
        mapping = {
            IntentCategory.CRUD: OperationType.WRITE,  # CRUD typically involves writes
            IntentCategory.IO: OperationType.WRITE,     # IO can be read or write, default to write
            IntentCategory.NETWORK: OperationType.NETWORK,
            IntentCategory.COMPUTATION: OperationType.EXECUTE
        }
        return mapping.get(intent, OperationType.NETWORK)
    
    def _determine_risk_level(self, side_effects: List[SideEffectType], operation_type: OperationType) -> RiskLevel:
        """
        Determine risk level based on side effects and operation type.
        
        Critical Logic:
        - NETWORK/IO with writes = HIGH
        - READ operations = LOW
        - DELETE operations = HIGH (minimum)
        """
        # DELETE operations are always HIGH+
        if operation_type == OperationType.DELETE:
            return RiskLevel.HIGH
        
        # Check for write/delete side effects
        write_effects = {
            SideEffectType.FILESYSTEM_WRITE,
            SideEffectType.FILESYSTEM_DELETE,
            SideEffectType.NETWORK_WRITE,
            SideEffectType.SYSTEM_EXEC,
            SideEffectType.STATE_MUTATION
        }
        
        has_write = any(effect in write_effects for effect in side_effects)
        
        if has_write:
            return RiskLevel.HIGH
        
        # Read-only operations
        read_effects = {
            SideEffectType.FILESYSTEM_READ,
            SideEffectType.NETWORK_READ
        }
        
        if all(effect in read_effects for effect in side_effects):
            return RiskLevel.LOW
        
        # Default to MEDIUM for mixed operations
        return RiskLevel.MEDIUM
    
    def _is_reversible(self, side_effects: List[SideEffectType], intent: IntentCategory) -> bool:
        """
        Determine if side effects are reversible.
        
        Read operations are always reversible (no side effects to reverse).
        Write operations are typically reversible if they don't involve deletion.
        """
        if not side_effects:
            return True  # No side effects = reversible
        
        # DELETE operations are typically not reversible
        if SideEffectType.FILESYSTEM_DELETE in side_effects:
            return False
        
        # Network writes might be reversible (e.g., can delete created resource)
        # System exec is typically not reversible
        if SideEffectType.SYSTEM_EXEC in side_effects:
            return False
        
        # Other write operations are typically reversible
        return True
    
    def _determine_scope(self, side_effects: List[SideEffectType]) -> str:
        """Determine scope of side effects"""
        network_effects = {
            SideEffectType.NETWORK_READ,
            SideEffectType.NETWORK_WRITE
        }
        
        if any(effect in network_effects for effect in side_effects):
            return "network"
        
        if SideEffectType.SYSTEM_EXEC in side_effects:
            return "external"
        
        return "local"
    
    def _generate_parameters(self, inputs: List[str]) -> List[CapabilityParameter]:
        """Generate parameter list from input names"""
        parameters = []
        
        for input_name in inputs:
            # Infer type from name
            param_type = self._infer_type_from_name(input_name)
            
            # Determine if sensitive
            sensitive_keywords = ["token", "key", "secret", "password", "credential", "auth", "api_key"]
            is_sensitive = any(keyword in input_name.lower() for keyword in sensitive_keywords)
            
            parameters.append(CapabilityParameter(
                name=input_name,
                type=param_type,
                description=f"{input_name.replace('_', ' ').title()} parameter",
                required=True,
                default=None
            ))
        
        return parameters
    
    def _infer_type_from_name(self, name: str) -> str:
        """Infer parameter type from name"""
        name_lower = name.lower()
        
        if any(keyword in name_lower for keyword in ["id", "count", "number", "index"]):
            return "number"
        elif any(keyword in name_lower for keyword in ["enabled", "active", "is_"]):
            return "boolean"
        elif any(keyword in name_lower for keyword in ["list", "array", "items"]):
            return "array"
        elif any(keyword in name_lower for keyword in ["config", "options", "params"]):
            return "object"
        else:
            return "string"  # Default
    
    def _generate_returns(self, outputs: List[str]) -> dict:
        """Generate returns schema from output names"""
        if not outputs:
            return {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "description": "Whether the operation succeeded"}
                }
            }
        
        properties = {}
        for output in outputs:
            output_type = self._infer_type_from_name(output)
            properties[output] = {
                "type": output_type,
                "description": f"{output.replace('_', ' ').title()} value"
            }
        
        return {
            "type": "object",
            "properties": properties
        }
    
    def _generate_name(self, action: str, target: str) -> str:
        """Generate human-readable name"""
        return f"{action.replace('_', ' ').title()} {target.title()}"
    
    def _generate_description(self, parsed: ParsedRequirement) -> str:
        """Generate capability description"""
        action_desc = parsed.action.replace('_', ' ')
        target_desc = parsed.target
        
        if parsed.missing_info:
            missing = ", ".join(parsed.missing_info[:3])  # Limit to first 3
            return f"Capability to {action_desc} on {target_desc}. Note: {missing} may need to be configured."
        
        return f"Capability to {action_desc} on {target_desc}."
    
    def _generate_risk_justification(self, parsed: ParsedRequirement, risk_level: RiskLevel) -> str:
        """Generate risk level justification"""
        if risk_level == RiskLevel.LOW:
            return "Read-only operation with no side effects"
        elif risk_level == RiskLevel.MEDIUM:
            return f"Operation with reversible side effects: {', '.join([e.value for e in parsed.side_effects])}"
        elif risk_level == RiskLevel.HIGH:
            return f"Operation with side effects: {', '.join([e.value for e in parsed.side_effects])}"
        else:
            return f"Critical operation requiring approval: {', '.join([e.value for e in parsed.side_effects])}"
    
    def _generate_side_effects_description(self, side_effects: List[SideEffectType]) -> str:
        """Generate side effects description"""
        if not side_effects:
            return "No side effects"
        
        return f"Side effects: {', '.join([e.value for e in side_effects])}"
    
    def _generate_tags(self, parsed: ParsedRequirement) -> List[str]:
        """Generate tags for the capability"""
        tags = [parsed.target, parsed.intent_category.value.lower()]
        
        if SideEffectType.NETWORK_READ in parsed.side_effects or SideEffectType.NETWORK_WRITE in parsed.side_effects:
            tags.append("network")
        
        if SideEffectType.FILESYSTEM_READ in parsed.side_effects or SideEffectType.FILESYSTEM_WRITE in parsed.side_effects:
            tags.append("filesystem")
        
        return tags
    
    def _generate_handler_path(self, capability_id: str) -> str:
        """Generate handler module path"""
        # Convert capability_id to module path
        # e.g., "net.crypto.get_price" -> "runtime.stdlib.generated.net_crypto_get_price"
        module_name = capability_id.replace(".", "_")
        return f"runtime.stdlib.generated.{module_name}"
