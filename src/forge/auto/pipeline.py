"""
AutoForge Pipeline - Main orchestration for converting requirements to capabilities.

This module stitches together all components into a single callable pipeline.
"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from .types import RawRequirement, ParsedRequirement
from .parser import RequirementParser
from .spec_gen import SpecGenerator
from .validator import SpecValidator
from .code_gen import CodeGenerator
from .test_gen import TestGenerator
from .reference_loader import ReferenceLoader
from .dependency_detector import DependencyDetector

# Import capability schema
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from specs.v3.capability_schema import CapabilitySpec


@dataclass
class ForgeResult:
    """
    Result of the AutoForge pipeline.
    
    Contains all generated files ready for Git commit.
    """
    capability_id: str
    spec: CapabilitySpec
    spec_yaml: str  # YAML content ready to write
    handler_code: str  # Python handler code
    test_code: str  # Python test code
    dependencies: Set[str]  # Detected dependencies
    requirements_snippet: str  # Requirements.txt snippet
    
    # File paths (relative to workspace)
    spec_path: str
    handler_path: str
    test_path: str


class AutoForge:
    """
    Main AutoForge pipeline.
    
    Orchestrates the complete flow from natural language requirement
    to fully compliant capability (Spec + Code + Test).
    """
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        max_retries: int = 3,
        provider: str = "auto"
    ):
        """
        Initialize AutoForge pipeline.
        
        Args:
            model: Model name to use for LLM operations
            max_retries: Maximum retries for validation
            provider: LLM provider ("openai", "deepseek", or "auto" for auto-detect)
        """
        self.provider = provider
        self.parser = RequirementParser(model=model, provider=provider)
        self.spec_gen = SpecGenerator()
        self.validator = SpecValidator(model=model, max_retries=max_retries, provider=provider)
        self.code_gen = CodeGenerator(model=model, provider=provider)
        self.test_gen = TestGenerator(model=model, provider=provider)
        self.reference_loader = ReferenceLoader()
        self.dependency_detector = DependencyDetector()
    
    def forge_capability(
        self,
        requirement: str,
        capability_id: Optional[str] = None,
        context: Optional[dict] = None,
        references: Optional[List[str]] = None,
        test_first: bool = False
    ) -> ForgeResult:
        """
        Forge a complete capability from a natural language requirement.
        
        Flow:
        1. Parse requirement (with references if provided)
        2. Generate spec
        3. Validate and fix spec
        4. Generate handler code (or test first if test_first=True)
        5. Generate test code
        
        Args:
            requirement: Natural language requirement
            capability_id: Optional capability ID (auto-generated if not provided)
            context: Optional context dictionary
            references: Optional list of reference file paths
            test_first: If True, generate tests before handler code (TDD mode)
        
        Returns:
            ForgeResult with all generated content
        """
        # Load references if provided
        references_content = None
        if references:
            ref_dict = self.reference_loader.load_references(references)
            references_content = self.reference_loader.format_for_prompt(ref_dict)
        
        # Step 1: Parse requirement
        raw_req = RawRequirement(description=requirement, context=context or {})
        parsed = self.parser.parse(requirement, context, references_content)
        
        # Step 2: Generate capability ID if not provided
        if not capability_id:
            capability_id = self._generate_capability_id(parsed)
        
        # Step 3: Generate spec
        spec = self.spec_gen.generate(parsed, capability_id)
        
        # Step 4: Validate and fix spec
        spec = self.validator.validate_and_fix(spec)
        
        # Step 5 & 6: Generate code (TDD mode: test first, then handler)
        if test_first:
            # TDD mode: Generate test cases first
            test_code = self.test_gen.generate_test_code(spec, None)  # No handler code yet
            # Then generate handler to satisfy tests
            handler_code = self.code_gen.generate_handler_code(spec, test_code)
        else:
            # Normal mode: Generate handler first, then tests
            handler_code = self.code_gen.generate_handler_code(spec)
            test_code = self.test_gen.generate_test_code(spec, handler_code)
        
        # Step 7: Detect dependencies
        all_code = handler_code + "\n" + test_code
        dependencies = self.dependency_detector.detect_from_code(all_code)
        requirements_snippet = self.dependency_detector.generate_requirements_snippet(dependencies)
        
        # Step 8: Convert spec to YAML
        spec_yaml = self._spec_to_yaml(spec)
        
        # Step 9: Generate file paths
        spec_path, handler_path, test_path = self._generate_file_paths(capability_id)
        
        return ForgeResult(
            capability_id=capability_id,
            spec=spec,
            spec_yaml=spec_yaml,
            handler_code=handler_code,
            test_code=test_code,
            dependencies=dependencies,
            requirements_snippet=requirements_snippet,
            spec_path=spec_path,
            handler_path=handler_path,
            test_path=test_path
        )
    
    def _generate_capability_id(self, parsed: ParsedRequirement) -> str:
        """
        Generate capability ID from parsed requirement.
        
        Format: {category}.{target}.{action}
        e.g., "net.crypto.get_price", "io.fs.read_file"
        """
        # Map intent category to prefix
        category_map = {
            "CRUD": "data",
            "IO": "io",
            "NETWORK": "net",
            "COMPUTATION": "compute"
        }
        
        category = category_map.get(parsed.intent_category.value, "net")
        target = parsed.target.lower().replace(" ", "_")
        action = parsed.action.lower().replace(" ", "_")
        
        return f"{category}.{target}.{action}"
    
    def _spec_to_yaml(self, spec: CapabilitySpec) -> str:
        """Convert CapabilitySpec to YAML string"""
        try:
            import yaml
        except ImportError:
            # Fallback to basic YAML-like format if yaml not available
            import json
            # Use mode='json' to serialize enums properly
            spec_dict = spec.model_dump(mode='json')
            return json.dumps(spec_dict, indent=2)
        
        # Use mode='json' to properly serialize enums and other non-JSON types
        spec_dict = spec.model_dump(mode='json')
        
        return yaml.dump(spec_dict, default_flow_style=False, sort_keys=False)
    
    def _generate_file_paths(self, capability_id: str) -> tuple[str, str, str]:
        """
        Generate file paths for spec, handler, and test.
        
        Returns:
            Tuple of (spec_path, handler_path, test_path)
        """
        # Convert capability_id to file-safe name
        file_name = capability_id.replace(".", "_")
        
        # Spec goes to capabilities/validated/generated/
        spec_path = f"capabilities/validated/generated/{capability_id}.yaml"
        
        # Handler goes to src/runtime/stdlib/generated/
        handler_path = f"src/runtime/stdlib/generated/{file_name}.py"
        
        # Test goes to tests/generated/
        test_path = f"tests/generated/test_{file_name}.py"
        
        return spec_path, handler_path, test_path
