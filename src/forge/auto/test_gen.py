"""
Test Generator - Generates pytest test code for handlers.

This module generates test files to verify handler functionality.
"""

import json
from typing import Optional

from .llm_client import LLMClient

# Import capability schema
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root / "src") not in sys.path:
    sys.path.insert(0, str(project_root / "src"))

from specs.v3.capability_schema import CapabilitySpec


class TestGenerator:
    """
    Generate pytest test code from CapabilitySpec and handler code.
    
    Creates comprehensive tests that mock external calls and verify
    handler behavior including undo functionality.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", provider: str = "auto"):
        """
        Initialize test generator.
        
        Args:
            model: Model name to use (default: gpt-4o-mini)
            provider: LLM provider ("openai", "deepseek", or "auto" for auto-detect)
        """
        self.model = model
        self.provider = provider
        self._llm_client = None  # Lazy initialization
    
    @property
    def client(self):
        """Lazy initialization of LLM client"""
        if self._llm_client is None:
            from .llm_client import create_llm_client
            self._llm_client = create_llm_client(
                provider=self.provider,
                model=self.model
            )
        return self._llm_client.client
    
    def generate_test_code(self, spec: CapabilitySpec, handler_code: Optional[str] = None) -> str:
        """
        Generate pytest test code.
        
        Args:
            spec: CapabilitySpec
            handler_code: Optional generated handler code (None for TDD mode)
        
        Returns:
            Python test code as string
        """
        prompt = self._build_test_prompt(spec, handler_code)
        test_code = self._call_llm(prompt)
        return self._clean_code(test_code)
    
    def _build_test_prompt(self, spec: CapabilitySpec, handler_code: Optional[str] = None) -> str:
        """Build prompt for test generation"""
        spec_dict = spec.model_dump(mode='json')
        capability_id = spec.id
        class_name = self._class_name_from_id(capability_id)
        has_undo = spec.compensation.supported
        parameters = {p.name: p.type for p in spec.parameters}
        
        handler_section = ""
        if handler_code:
            handler_section = f"""
**Handler Code:**
```python
{handler_code}
```
"""
        else:
            handler_section = """
**Test-Driven Development Mode:**
Generate comprehensive test cases FIRST, before handler implementation.
The handler will be generated later to satisfy these tests.
Focus on:
- Complete test coverage
- Edge cases
- Error scenarios
- Clear test descriptions
"""
        
        return f"""You are a pytest test generator for AI-First Runtime handlers.
{handler_section}

Generate a complete pytest test file for the following handler:

**Capability ID:** {capability_id}
**Handler Class:** {class_name}
**Supports Undo:** {has_undo}
**Parameters:** {json.dumps(parameters, indent=2)}

**Spec (JSON):**
{json.dumps(spec_dict, indent=2)}

**Requirements:**
1. Use pytest and unittest.mock
2. Mock all external calls (httpx, requests, filesystem, etc.)
3. Test successful execution
4. Test parameter validation (missing required params, wrong types)
5. Test error handling (network errors, file errors, etc.)
6. If undo is supported, test that undo_closure is created and works
7. Verify that ActionOutput structure is correct
8. Use fixtures for common setup (spec dict, context mock)
9. Test edge cases (empty inputs, None values, etc.)

**Example Structure:**
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from runtime.types import ActionOutput, ExecutionContext
from runtime.handler import ActionHandler
from {spec.handler or 'runtime.stdlib.generated'} import {class_name}

@pytest.fixture
def spec_dict():
    return {json.dumps(spec_dict, indent=8)}

@pytest.fixture
def context():
    ctx = Mock(spec=ExecutionContext)
    ctx.workspace_root = Path("/tmp/test_workspace")
    ctx.user_id = "test_user"
    ctx.session_id = "test_session"
    return ctx

class Test{class_name}:
    def test_execute_success(self, spec_dict, context):
        # Test successful execution
        handler = {class_name}(spec_dict)
        params = {{...}}  # Valid parameters
        
        with patch(...):  # Mock external calls
            result = handler.execute(params, context)
            
            assert isinstance(result, ActionOutput)
            assert "result" in result.result
            # ... more assertions ...
    
    def test_execute_with_undo(self, spec_dict, context):
        # Test undo closure creation (if supported)
        if {str(has_undo).lower()}:
            handler = {class_name}(spec_dict)
            params = {{...}}
            
            with patch(...):
                result = handler.execute(params, context)
                
                assert result.undo_closure is not None
                # Test that undo actually works
                result.undo_closure()
                # ... verify undo effects ...
    
    def test_validate_params_missing_required(self, spec_dict, context):
        # Test parameter validation
        handler = {class_name}(spec_dict)
        params = {{}}  # Missing required params
        
        with pytest.raises(ValueError):
            handler.execute(params, context)
    
    def test_handle_network_error(self, spec_dict, context):
        # Test error handling
        handler = {class_name}(spec_dict)
        params = {{...}}
        
        with patch(..., side_effect=Exception("Network error")):
            with pytest.raises(Exception):
                handler.execute(params, context)
```

**Important:**
- Mock all external dependencies (httpx.get, httpx.post, open, etc.)
- Test both success and failure cases
- Verify undo closure captures correct state
- Use proper pytest patterns (fixtures, parametrize if needed)
- Test all parameters and edge cases

Output ONLY the Python test code, no explanations or markdown code blocks.
"""
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM to generate test code"""
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
                {"role": "system", "content": "You are a pytest test generator. Output only valid Python code, no markdown or explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def _clean_code(self, code: str) -> str:
        """Clean generated code (remove markdown if present)"""
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        
        if code.endswith("```"):
            code = code[:-3]
        
        return code.strip()
    
    def _class_name_from_id(self, capability_id: str) -> str:
        """Convert capability ID to class name"""
        parts = capability_id.split(".")
        last_part = parts[-1]
        words = last_part.split("_")
        class_name = "".join(word.capitalize() for word in words) + "Handler"
        return class_name
