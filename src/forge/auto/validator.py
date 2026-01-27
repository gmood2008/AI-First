"""
Validator - Ensures generated spec is valid BEFORE generating code.

This module implements a retry loop with self-healing logic to fix validation issues.
"""

from typing import List, Optional
import json

from .llm_client import LLMClient
from .types import SideEffectType

# Import capability schema
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from specs.v3.capability_schema import CapabilitySpec, RiskLevel, OperationType


class SpecValidator:
    """
    Validate and fix CapabilitySpec using self-healing logic.
    
    Implements a retry loop that uses LLM to fix validation issues.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", max_retries: int = 3, provider: str = "auto"):
        """
        Initialize validator.
        
        Args:
            model: Model name to use for fixing issues
            max_retries: Maximum number of retry attempts
            provider: LLM provider ("openai", "deepseek", or "auto" for auto-detect)
        """
        self.model = model
        self.max_retries = max_retries
        self.provider = provider
        self._llm_client = None  # Lazy initialization
    
    def validate_and_fix(self, spec: CapabilitySpec) -> CapabilitySpec:
        """
        Validate spec and fix issues using self-healing logic.
        
        Args:
            spec: CapabilitySpec to validate
        
        Returns:
            Validated (and potentially fixed) CapabilitySpec
        """
        for attempt in range(self.max_retries):
            issues = self._validate(spec)
            
            if not issues:
                return spec  # Valid!
            
            if attempt < self.max_retries - 1:
                # Try to fix issues
                spec = self._fix_issues(spec, issues)
            else:
                # Last attempt - raise error with all issues
                raise ValueError(
                    f"Failed to generate valid spec after {self.max_retries} attempts. "
                    f"Issues: {', '.join(issues)}"
                )
        
        return spec
    
    def _validate(self, spec: CapabilitySpec) -> List[str]:
        """
        Validate spec and return list of issues.
        
        Args:
            spec: CapabilitySpec to validate
        
        Returns:
            List of validation issue messages (empty if valid)
        """
        issues = []
        
        # 1. Check risk consistency (v3 schema has built-in validation, but we check manually too)
        try:
            # This will raise ValueError if risk consistency check fails
            spec.model_post_init(None)
        except ValueError as e:
            issues.append(str(e))
        
        # 2. Check if write operations have compensation
        write_ops = {
            OperationType.WRITE,
            OperationType.DELETE,
            OperationType.NETWORK  # Network can be write
        }
        
        has_write_side_effects = any(
            effect in [SideEffectType.FILESYSTEM_WRITE, SideEffectType.FILESYSTEM_DELETE,
                      SideEffectType.NETWORK_WRITE, SideEffectType.SYSTEM_EXEC,
                      SideEffectType.STATE_MUTATION]
            for effect in [se for se in SideEffectType]  # This is a placeholder - we need to check actual side effects
        )
        
        # Check if side effects are write operations
        # Since SideEffects in v3 schema doesn't have a list, we check the description
        # or we need to infer from operation_type
        if spec.operation_type in write_ops and not spec.side_effects.reversible:
            if not spec.compensation.supported:
                issues.append(
                    f"Write operation with irreversible side effects must have compensation.supported=True"
                )
        
        # 3. Check if DELETE operations have HIGH+ risk
        if spec.operation_type == OperationType.DELETE:
            if spec.risk.level not in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                issues.append(
                    f"DELETE operations require HIGH or CRITICAL risk level, got {spec.risk.level.value}"
                )
        
        # 4. Check if parameters have descriptions
        for param in spec.parameters:
            if not param.description or len(param.description.strip()) == 0:
                issues.append(f"Parameter '{param.name}' is missing description")
        
        # 5. Check if description is meaningful
        if not spec.description or len(spec.description.strip()) < 10:
            issues.append("Capability description is too short or empty")
        
        return issues
    
    def _fix_issues(self, spec: CapabilitySpec, issues: List[str]) -> CapabilitySpec:
        """
        Fix validation issues using LLM.
        
        Args:
            spec: CapabilitySpec with issues
            issues: List of issue messages
        
        Returns:
            Fixed CapabilitySpec
        """
        prompt = self._build_fix_prompt(spec, issues)
        fixed_dict = self._call_llm_for_fix(prompt)
        
        # Apply fixes to spec
        return self._apply_fixes(spec, fixed_dict, issues)
    
    def _build_fix_prompt(self, spec: CapabilitySpec, issues: List[str]) -> str:
        """Build prompt for fixing issues"""
        spec_dict = spec.model_dump(mode='json')
        issues_str = "\n".join([f"- {issue}" for issue in issues])
        
        return f"""You are a capability specification fixer for AI-First Runtime.

The following CapabilitySpec has validation issues:

**Spec (JSON):**
{json.dumps(spec_dict, indent=2)}

**Issues:**
{issues_str}

**Your Task:**
Fix the issues by providing a JSON object with ONLY the fields that need to be changed.
For example:
- If risk level needs to be upgraded: {{"risk": {{"level": "HIGH"}}}}
- If compensation needs to be enabled: {{"compensation": {{"supported": true}}}}
- If description needs improvement: {{"description": "Better description here"}}

**Rules:**
1. Only fix the specific issues mentioned
2. Maintain consistency with v3 schema validation rules
3. If risk level mismatch, upgrade to appropriate level
4. If missing undo strategy, set compensation.supported=true and provide strategy
5. Keep all other fields unchanged

Output ONLY valid JSON with the fields to update, no explanations.
"""
    
    @property
    def client(self):
        """Lazy initialization of OpenAI client"""
        if self._client is None:
            self._client = OpenAI()
        return self._client
    
    def _call_llm_for_fix(self, prompt: str) -> dict:
        """Call LLM to get fixes"""
        # Get actual model name (may be mapped for DeepSeek)
        if self._llm_client is None:
            from .llm_client import create_llm_client
            self._llm_client = create_llm_client(
                provider=self.provider,
                model=self.model
            )
        actual_model = self._llm_client.get_model_name()
        
        response = self.client.chat.completions.create(
            model=actual_model,
            messages=[
                {"role": "system", "content": "You are a capability specification fixer. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nContent: {content}")
    
    def _apply_fixes(self, spec: CapabilitySpec, fixes: dict, issues: List[str]) -> CapabilitySpec:
        """Apply fixes to spec"""
        spec_dict = spec.model_dump(mode='json')
        
        # Apply fixes
        if "risk" in fixes:
            if "level" in fixes["risk"]:
                spec_dict["risk"]["level"] = fixes["risk"]["level"]
            if "justification" in fixes["risk"]:
                spec_dict["risk"]["justification"] = fixes["risk"]["justification"]
            if "requires_approval" in fixes["risk"]:
                spec_dict["risk"]["requires_approval"] = fixes["risk"]["requires_approval"]
        
        if "compensation" in fixes:
            if "supported" in fixes["compensation"]:
                spec_dict["compensation"]["supported"] = fixes["compensation"]["supported"]
            if "strategy" in fixes["compensation"]:
                spec_dict["compensation"]["strategy"] = fixes["compensation"]["strategy"]
        
        if "side_effects" in fixes:
            if "reversible" in fixes["side_effects"]:
                spec_dict["side_effects"]["reversible"] = fixes["side_effects"]["reversible"]
        
        if "description" in fixes:
            spec_dict["description"] = fixes["description"]
        
        # Auto-fix common issues
        for issue in issues:
            if "risk level mismatch" in issue.lower() or "risk level" in issue.lower():
                # Auto-upgrade risk level if needed
                if spec.operation_type == OperationType.DELETE:
                    spec_dict["risk"]["level"] = RiskLevel.HIGH.value
                elif "irreversible" in issue.lower():
                    spec_dict["risk"]["level"] = RiskLevel.HIGH.value
            
            if "compensation" in issue.lower() and "supported" in issue.lower():
                spec_dict["compensation"]["supported"] = True
                if not spec_dict["compensation"].get("strategy"):
                    spec_dict["compensation"]["strategy"] = "automatic"
        
        # Recreate spec from fixed dict
        try:
            return CapabilitySpec(**spec_dict)
        except Exception as e:
            raise ValueError(f"Failed to apply fixes: {e}\nFixes: {fixes}")
