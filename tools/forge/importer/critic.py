"""
Critic Agent for validating generated capability specifications.
"""

from typing import List
from .types import CapabilitySpec, ValidationResult, SideEffectType


class SpecCritic:
    """Validate capability specifications for safety and completeness"""
    
    # Side effects that require undo strategy
    WRITE_SIDE_EFFECTS = [
        "filesystem_write",
        "filesystem_delete",
        "network_write",
        "system_exec",
        "state_mutation",
    ]
    
    # Valid enum values
    VALID_SIDE_EFFECTS = [
        "filesystem_read",
        "filesystem_write",
        "filesystem_delete",
        "network_read",
        "network_write",
        "system_exec",
        "state_mutation",
    ]
    
    VALID_COST_MODELS = ["free", "low_io", "high_io", "network", "compute"]
    
    # Generic/invalid undo strategies
    INVALID_UNDO_STRATEGIES = [
        "n/a",
        "none",
        "not applicable",
        "cannot undo",
        "no undo",
        "",
    ]
    
    def validate(self, spec: CapabilitySpec) -> ValidationResult:
        """
        Validate capability specification.
        
        Args:
            spec: Capability specification to validate
        
        Returns:
            ValidationResult with issues and warnings
        """
        issues = []
        warnings = []
        
        # 1. Schema validation
        schema_issues = self._validate_schema(spec)
        issues.extend(schema_issues)
        
        # 2. Safety checks
        safety_issues, safety_warnings = self._validate_safety(spec)
        issues.extend(safety_issues)
        warnings.extend(safety_warnings)
        
        # 3. Completeness checks
        completeness_issues = self._validate_completeness(spec)
        issues.extend(completeness_issues)
        
        # 4. Undo strategy validation
        undo_issues, undo_warnings = self._validate_undo_strategy(spec)
        issues.extend(undo_issues)
        warnings.extend(undo_warnings)
        
        return ValidationResult(
            valid=len(issues) == 0,
            issues=issues,
            warnings=warnings,
        )
    
    def _validate_schema(self, spec: CapabilitySpec) -> List[str]:
        """Validate schema structure and enum values"""
        issues = []
        
        # Check side_effects enum
        for effect in spec.contracts.side_effects:
            if effect not in self.VALID_SIDE_EFFECTS:
                issues.append(f"Invalid side_effect value: '{effect}'. Must be one of {self.VALID_SIDE_EFFECTS}")
        
        # Check cost_model enum
        if spec.behavior.cost_model not in self.VALID_COST_MODELS:
            issues.append(f"Invalid cost_model value: '{spec.behavior.cost_model}'. Must be one of {self.VALID_COST_MODELS}")
        
        # Check parameter types
        for param_name, param in spec.interface.inputs.items():
            if param.type not in ["string", "integer", "float", "boolean", "array", "object"]:
                issues.append(f"Invalid parameter type for '{param_name}': '{param.type}'")
        
        # Check output types
        for output_name, output in spec.interface.outputs.items():
            if output.type not in ["string", "integer", "float", "boolean", "array", "object"]:
                issues.append(f"Invalid output type for '{output_name}': '{output.type}'")
        
        return issues
    
    def _validate_safety(self, spec: CapabilitySpec) -> tuple[List[str], List[str]]:
        """Validate safety requirements"""
        issues = []
        warnings = []
        
        # Check if write operations require confirmation
        has_write_effects = any(
            effect in self.WRITE_SIDE_EFFECTS
            for effect in spec.contracts.side_effects
        )
        
        if has_write_effects:
            # Destructive operations should require confirmation (warning, not error)
            if not spec.contracts.requires_confirmation:
                if "filesystem_delete" in spec.contracts.side_effects or "system_exec" in spec.contracts.side_effects:
                    warnings.append(
                        f"Destructive operation ({spec.meta.id}) does not require confirmation. "
                        "Consider setting requires_confirmation=true for safety."
                    )
        
        # Check if sensitive parameters are marked
        for param_name, param in spec.interface.inputs.items():
            if any(keyword in param_name.lower() for keyword in ["token", "key", "secret", "password", "credential"]):
                if not param.sensitive:
                    warnings.append(f"Parameter '{param_name}' appears sensitive but is not marked as sensitive=true")
        
        return issues, warnings
    
    def _validate_completeness(self, spec: CapabilitySpec) -> List[str]:
        """Validate completeness of specification"""
        issues = []
        
        # Check meta fields
        if not spec.meta.description or len(spec.meta.description.strip()) == 0:
            issues.append("meta.description is empty")
        
        # Check all parameters have descriptions
        for param_name, param in spec.interface.inputs.items():
            if not param.description or len(param.description.strip()) == 0:
                issues.append(f"Parameter '{param_name}' has no description")
        
        # Check all outputs have descriptions
        for output_name, output in spec.interface.outputs.items():
            if not output.description or len(output.description.strip()) == 0:
                issues.append(f"Output '{output_name}' has no description")
        
        # Check at least one output exists
        if len(spec.interface.outputs) == 0:
            issues.append("No outputs defined in interface")
        
        return issues
    
    def _validate_undo_strategy(self, spec: CapabilitySpec) -> tuple[List[str], List[str]]:
        """Validate undo strategy for write operations"""
        issues = []
        warnings = []
        
        # Check if write operations have undo strategy
        has_write_effects = any(
            effect in self.WRITE_SIDE_EFFECTS
            for effect in spec.contracts.side_effects
        )
        
        if has_write_effects:
            undo_strategy = spec.behavior.undo_strategy.strip().lower()
            
            # Check if undo_strategy is empty or invalid
            if not undo_strategy or undo_strategy in self.INVALID_UNDO_STRATEGIES:
                issues.append(
                    f"Write operation ({spec.meta.id}) requires a specific undo_strategy. "
                    f"Generic values like 'N/A', 'None', or empty strings are not acceptable. "
                    f"Provide a concrete description of how to undo this operation."
                )
            
            # Check if undo_strategy is too short (likely generic)
            elif len(undo_strategy) < 20:
                warnings.append(
                    f"Undo strategy for {spec.meta.id} is very short ({len(undo_strategy)} chars). "
                    f"Consider providing more detail on how to undo this operation."
                )
            
            # Check for vague language
            vague_phrases = ["if possible", "may be able", "try to", "attempt to", "might"]
            if any(phrase in undo_strategy for phrase in vague_phrases):
                warnings.append(
                    f"Undo strategy for {spec.meta.id} contains vague language. "
                    f"Be specific about how undo will be performed."
                )
        
        return issues, warnings
    
    def format_validation_report(self, result: ValidationResult) -> str:
        """Format validation result as human-readable report"""
        if result.valid and not result.warnings:
            return "✅ Validation passed with no issues"
        
        lines = []
        
        if result.issues:
            lines.append("❌ Validation FAILED with the following issues:")
            for i, issue in enumerate(result.issues, 1):
                lines.append(f"  {i}. {issue}")
        
        if result.warnings:
            lines.append("\n⚠️  Warnings:")
            for i, warning in enumerate(result.warnings, 1):
                lines.append(f"  {i}. {warning}")
        
        if result.valid and result.warnings:
            lines.insert(0, "✅ Validation passed with warnings:")
        
        return "\n".join(lines)
