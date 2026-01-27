"""
Smart Importer main logic - orchestrates the import process.
"""

import yaml
from pathlib import Path
from typing import Optional, Tuple

from .types import SourceType, FunctionInfo, EndpointInfo, CapabilitySpec, ValidationResult
from .python_parser import PythonParser
from .openapi_parser import OpenAPIParser
from .llm_generator import LLMSpecGenerator
from .critic import SpecCritic
from .scaffolder import HandlerScaffolder


class SmartImporter:
    """Main importer class that orchestrates the import process"""
    
    def __init__(self, model: str = "gpt-4.1-mini", max_retries: int = 3):
        """
        Initialize Smart Importer.
        
        Args:
            model: LLM model to use for spec generation
            max_retries: Maximum retries for LLM generation with feedback
        """
        self.python_parser = PythonParser()
        self.openapi_parser = OpenAPIParser()
        self.llm_generator = LLMSpecGenerator(model=model)
        self.critic = SpecCritic()
        self.scaffolder = HandlerScaffolder()
        self.max_retries = max_retries
    
    def import_from_source(
        self,
        source: str,
        capability_id: str,
        output_dir: str = "./capabilities",
        function_name: Optional[str] = None,
        endpoint_path: Optional[str] = None,
        method: Optional[str] = None,
        generate_handler: bool = True,
        generate_tests: bool = True,
        dry_run: bool = False,
        verbose: bool = False,
    ) -> Tuple[CapabilitySpec, ValidationResult, Optional[Path], Optional[Path]]:
        """
        Import capability from source.
        
        Args:
            source: Source file path, code string, or URL
            capability_id: Desired capability ID (e.g., "tools.slack.send_message")
            output_dir: Output directory for generated files
            function_name: Specific function to import (for Python sources)
            endpoint_path: Specific endpoint path (for OpenAPI sources)
            method: Specific HTTP method (for OpenAPI sources)
            generate_handler: Whether to generate handler code
            generate_tests: Whether to generate test code
            dry_run: If True, don't write files
            verbose: If True, print detailed progress
        
        Returns:
            Tuple of (spec, validation_result, handler_file, test_file)
        """
        # Step 1: Detect source type
        source_type = self._detect_source_type(source)
        if verbose:
            print(f"📋 Detected source type: {source_type.value}")
        
        # Step 2: Parse source
        if verbose:
            print(f"🔍 Parsing source...")
        
        if source_type in [SourceType.PYTHON_FILE, SourceType.PYTHON_CODE]:
            func_info = self._parse_python_source(source, source_type, function_name)
            if verbose:
                print(f"✅ Parsed function: {func_info.name}")
                print(f"   Parameters: {[p.name for p in func_info.parameters]}")
                print(f"   Side effects: {func_info.side_effects}")
            
            # Step 3: Generate spec with LLM
            spec = self._generate_spec_with_retry(func_info, capability_id, verbose)
            
        elif source_type == SourceType.OPENAPI_SPEC:
            endpoint_info = self._parse_openapi_source(source, endpoint_path, method)
            if verbose:
                print(f"✅ Parsed endpoint: {endpoint_info.method} {endpoint_info.path}")
                print(f"   Parameters: {[p.name for p in endpoint_info.parameters]}")
                print(f"   Side effects: {endpoint_info.side_effects}")
            
            # Step 3: Generate spec with LLM
            spec = self._generate_spec_with_retry(endpoint_info, capability_id, verbose)
            func_info = None
        
        else:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        # Step 4: Validate spec with Critic
        if verbose:
            print(f"\n🔍 Validating spec with Critic Agent...")
        
        validation = self.critic.validate(spec)
        
        if verbose:
            print(self.critic.format_validation_report(validation))
        
        if not validation.valid:
            raise ValueError(f"Spec validation failed:\n{self.critic.format_validation_report(validation)}")
        
        # Step 5: Write files
        handler_file = None
        test_file = None
        
        if not dry_run:
            output_path = Path(output_dir)
            
            # Write YAML spec
            spec_file = output_path / f"{spec.meta.id}.yaml"
            spec_file.parent.mkdir(parents=True, exist_ok=True)
            with open(spec_file, 'w') as f:
                yaml.dump(spec.to_dict(), f, default_flow_style=False, sort_keys=False)
            
            if verbose:
                print(f"\n✅ Wrote spec to: {spec_file}")
            
            # Generate handler code
            if generate_handler:
                handler_file, test_file = self.scaffolder.write_files(
                    spec, output_path, func_info if source_type in [SourceType.PYTHON_FILE, SourceType.PYTHON_CODE] else None, generate_tests
                )
                if verbose:
                    print(f"✅ Wrote handler to: {handler_file}")
                    if test_file:
                        print(f"✅ Wrote tests to: {test_file}")
        else:
            if verbose:
                print(f"\n🔍 Dry run - no files written")
        
        return spec, validation, handler_file, test_file
    
    def _detect_source_type(self, source: str) -> SourceType:
        """Detect the type of source"""
        if source.startswith("http://") or source.startswith("https://"):
            return SourceType.URL
        elif Path(source).exists():
            if source.endswith(".py"):
                return SourceType.PYTHON_FILE
            elif source.endswith((".yaml", ".yml", ".json")):
                return SourceType.OPENAPI_SPEC
            else:
                raise ValueError(f"Unknown file type: {source}")
        else:
            # Assume it's Python code string
            return SourceType.PYTHON_CODE
    
    def _parse_python_source(self, source: str, source_type: SourceType, function_name: Optional[str]) -> FunctionInfo:
        """Parse Python source and extract function info"""
        if source_type == SourceType.PYTHON_FILE:
            functions = self.python_parser.parse_file(source, function_name)
        else:
            functions = self.python_parser.parse_code(source, function_name)
        
        if len(functions) == 0:
            raise ValueError("No functions found in source")
        elif len(functions) > 1:
            raise ValueError(f"Multiple functions found. Please specify --function. Found: {[f.name for f in functions]}")
        
        return functions[0]
    
    def _parse_openapi_source(self, source: str, endpoint_path: Optional[str], method: Optional[str]) -> EndpointInfo:
        """Parse OpenAPI source and extract endpoint info"""
        endpoints = self.openapi_parser.parse_file(source, endpoint_path, method)
        
        if len(endpoints) == 0:
            raise ValueError("No endpoints found in spec")
        elif len(endpoints) > 1:
            raise ValueError(f"Multiple endpoints found. Please specify --endpoint and --method. Found: {[(e.method, e.path) for e in endpoints]}")
        
        return endpoints[0]
    
    def _generate_spec_with_retry(self, info: FunctionInfo | EndpointInfo, capability_id: str, verbose: bool) -> CapabilitySpec:
        """Generate spec with LLM and retry with feedback if validation fails"""
        for attempt in range(self.max_retries):
            if verbose:
                print(f"\n🤖 Generating spec with LLM (attempt {attempt + 1}/{self.max_retries})...")
            
            # Generate spec
            if isinstance(info, FunctionInfo):
                spec = self.llm_generator.generate_from_function(info, capability_id)
            else:
                spec = self.llm_generator.generate_from_endpoint(info, capability_id)
            
            # Validate with Critic
            validation = self.critic.validate(spec)
            
            if validation.valid:
                if verbose:
                    print(f"✅ Spec generated successfully")
                return spec
            
            # If validation failed, prepare feedback for retry
            if attempt < self.max_retries - 1:
                if verbose:
                    print(f"⚠️  Validation failed, retrying with feedback...")
                    print(f"   Issues: {validation.issues}")
                # TODO: Implement feedback loop to LLM with validation issues
                # For now, just retry with same prompt
            else:
                # Max retries reached
                raise ValueError(f"Failed to generate valid spec after {self.max_retries} attempts:\n{self.critic.format_validation_report(validation)}")
        
        raise ValueError("Unexpected error in spec generation")
