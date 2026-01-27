"""
External Capability Importer

Imports third-party capabilities (Claude Skills, OpenAI Functions, etc.)
and converts them to AI-First format.
"""

import json
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from .skill_converter import SkillConverter
from .pipeline import AutoForge
from specs.v3.capability_schema import CapabilitySpec


class ExternalImporter:
    """
    Import external capabilities and convert to AI-First format.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", provider: str = "auto"):
        """
        Initialize external importer.
        
        Args:
            model: LLM model for enhancement
            provider: LLM provider
        """
        self.converter = SkillConverter()
        self.autoforge = AutoForge(model=model, provider=provider)
    
    def import_claude_skill(
        self,
        skill_source: str,
        capability_id: str,
        output_dir: str = "capabilities/validated/external",
        api_key: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Import Claude Skill from URL or file.
        
        Args:
            skill_source: URL or file path to Claude Skill definition
            capability_id: Desired AI-First capability ID
            output_dir: Output directory for generated files
            api_key: Claude API key (or use CLAUDE_API_KEY env var)
            dry_run: If True, don't save files
        
        Returns:
            Dictionary with import results
        """
        # Load skill definition
        skill_def = self._load_skill_definition(skill_source)
        
        # Extract skill ID if from URL
        skill_id = None
        if skill_source.startswith("http"):
            # Try to extract skill ID from URL
            # e.g., https://api.anthropic.com/v1/skills/123 -> 123
            parts = skill_source.rstrip("/").split("/")
            if "skills" in parts:
                skill_id = parts[parts.index("skills") + 1]
        
        # Create adapter config
        adapter_config = {
            "capability_id": capability_id,
            "skill_id": skill_id or skill_def.get("id"),
            "api_key": api_key,
            "api_key_env": "CLAUDE_API_KEY",
            "base_url": "https://api.anthropic.com/v1"
        }
        
        # Convert to AI-First spec
        spec = self.converter.convert_claude_skill(
            skill_definition=skill_def,
            capability_id=capability_id,
            adapter_config=adapter_config
        )
        
        # Generate handler wrapper
        handler_code = self.converter.generate_handler_wrapper(
            spec=spec,
            adapter_type="claude_skill",
            adapter_config=adapter_config
        )
        
        # Generate test code (basic)
        test_code = self._generate_basic_test(spec, handler_code)
        
        # Convert spec to YAML and add adapter config
        spec_dict = spec.model_dump(mode='json')
        
        # Add adapter configuration to the YAML (at top level)
        spec_dict["adapter"] = {
            "type": "claude_skill",
            "config": adapter_config
        }
        
        spec_yaml = yaml.dump(spec_dict, default_flow_style=False, sort_keys=False)
        
        if not dry_run:
            # Save files
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Save spec
            spec_file = output_path / f"{capability_id}.yaml"
            spec_file.write_text(spec_yaml)
            
            # Save handler
            handler_file = Path(f"src/runtime/stdlib/generated/{capability_id.replace('.', '_')}.py")
            handler_file.parent.mkdir(parents=True, exist_ok=True)
            handler_file.write_text(handler_code)
            
            # Save test
            test_file = Path(f"tests/generated/test_{capability_id.replace('.', '_')}.py")
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(test_code)
        
        return {
            "capability_id": capability_id,
            "spec": spec,
            "spec_yaml": spec_yaml,
            "handler_code": handler_code,
            "test_code": test_code,
            "spec_path": str(Path(output_dir) / f"{capability_id}.yaml"),
            "handler_path": str(handler_file) if not dry_run else None,
            "test_path": str(test_file) if not dry_run else None,
        }
    
    def import_http_api(
        self,
        api_definition: Dict[str, Any],
        capability_id: str,
        output_dir: str = "capabilities/validated/external",
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Import HTTP API as AI-First capability.
        
        Args:
            api_definition: HTTP API definition
            capability_id: Desired AI-First capability ID
            output_dir: Output directory
            dry_run: If True, don't save files
        
        Returns:
            Dictionary with import results
        """
        # Create adapter config
        adapter_config = {
            "capability_id": capability_id,
            "endpoint_url": api_definition.get("endpoint_url"),
            "method": api_definition.get("method", "POST"),
            "headers": api_definition.get("headers", {}),
            "auth_type": api_definition.get("auth_type", "none"),
            "auth_config": api_definition.get("auth_config", {}),
            "timeout": api_definition.get("timeout", 30.0)
        }
        
        # Convert to AI-First spec
        spec = self.converter.convert_http_api(
            api_definition=api_definition,
            capability_id=capability_id,
            adapter_config=adapter_config
        )
        
        # Generate handler wrapper
        handler_code = self.converter.generate_handler_wrapper(
            spec=spec,
            adapter_type="http_api",
            adapter_config=adapter_config
        )
        
        # Generate test code
        test_code = self._generate_basic_test(spec, handler_code)
        
        # Convert spec to YAML and add adapter config
        spec_dict = spec.model_dump(mode='json')
        
        # Add adapter configuration
        spec_dict["adapter"] = {
            "type": "http_api",
            "config": adapter_config
        }
        
        spec_yaml = yaml.dump(spec_dict, default_flow_style=False, sort_keys=False)
        
        if not dry_run:
            # Save files
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            spec_file = output_path / f"{capability_id}.yaml"
            spec_file.write_text(spec_yaml)
            
            handler_file = Path(f"src/runtime/stdlib/generated/{capability_id.replace('.', '_')}.py")
            handler_file.parent.mkdir(parents=True, exist_ok=True)
            handler_file.write_text(handler_code)
            
            test_file = Path(f"tests/generated/test_{capability_id.replace('.', '_')}.py")
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text(test_code)
        
        return {
            "capability_id": capability_id,
            "spec": spec,
            "spec_yaml": spec_yaml,
            "handler_code": handler_code,
            "test_code": test_code,
            "spec_path": str(Path(output_dir) / f"{capability_id}.yaml"),
            "handler_path": str(handler_file) if not dry_run else None,
            "test_path": str(test_file) if not dry_run else None,
        }
    
    def _load_skill_definition(self, source: str) -> Dict[str, Any]:
        """
        Load skill definition from URL or file.
        
        Args:
            source: URL or file path
        
        Returns:
            Skill definition dictionary
        """
        if source.startswith("http://") or source.startswith("https://"):
            # Load from URL
            try:
                with httpx.Client(timeout=30.0) as client:
                    response = client.get(source)
                    response.raise_for_status()
                    return response.json()
            except Exception as e:
                raise ValueError(f"Failed to load skill from URL: {e}")
        else:
            # Load from file
            path = Path(source)
            if not path.exists():
                raise FileNotFoundError(f"Skill definition file not found: {source}")
            
            with open(path, "r") as f:
                if path.suffix == ".json":
                    return json.load(f)
                elif path.suffix in [".yaml", ".yml"]:
                    return yaml.safe_load(f)
                else:
                    # Try JSON first, then YAML
                    try:
                        return json.load(f)
                    except:
                        f.seek(0)
                        return yaml.safe_load(f)
    
    def _generate_basic_test(self, spec: CapabilitySpec, handler_code: str) -> str:
        """Generate basic test code for external capability"""
        class_name = spec.id.split(".")[-1].capitalize() + "Handler"
        
        test_code = f'''"""
Basic tests for external capability: {spec.id}
"""

import pytest
from unittest.mock import Mock, patch
from runtime.types import ActionOutput, ExecutionContext
from runtime.stdlib.generated.{spec.id.replace(".", "_")} import {class_name}

@pytest.fixture
def spec_dict():
    """Load spec from YAML"""
    import yaml
    from pathlib import Path
    spec_file = Path("capabilities/validated/external/{spec.id}.yaml")
    with open(spec_file, "r") as f:
        return yaml.safe_load(f)

@pytest.fixture
def handler(spec_dict):
    """Create handler instance"""
    return {class_name}(spec_dict)

@pytest.fixture
def context():
    """Create execution context"""
    from runtime.types import ExecutionContext
    from pathlib import Path
    return ExecutionContext(
        user_id="test_user",
        workspace_root=Path("/tmp/test_workspace"),
        session_id="test_session",
        confirmation_callback=None,
        undo_enabled=False
    )

def test_handler_initialization(handler):
    """Test handler can be initialized"""
    assert handler is not None
    assert handler.capability_id == "{spec.id}"

def test_execute_basic(handler, context):
    """Test basic execution (mocked)"""
    # Mock the adapter
    with patch.object(handler, 'adapter') as mock_adapter:
        mock_result = ActionOutput(
            result={{"result": "test"}},
            description="Test execution",
            undo_closure=None
        )
        mock_adapter.create_handler.return_value.execute.return_value = mock_result
        
        result = handler.execute({{"test_param": "value"}}, context)
        
        assert result is not None
        assert "result" in result.result
'''
        
        return test_code
