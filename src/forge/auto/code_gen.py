"""
Code Generator - Generates Python handler code from CapabilitySpec.

This module generates the actual Python code for the Handler class.
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


class CodeGenerator:
    """
    Generate Python handler code from CapabilitySpec.
    
    Creates a Python class that inherits from ActionHandler and implements
    the execute method with proper undo closure support.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", provider: str = "auto"):
        """
        Initialize code generator.
        
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
    
    def generate_handler_code(self, spec: CapabilitySpec, test_code: Optional[str] = None) -> str:
        """
        Generate Python handler code from spec.
        
        Args:
            spec: CapabilitySpec to generate code for
            test_code: Optional test code (for TDD mode - generate handler to satisfy tests)
        
        Returns:
            Python code as string
        """
        prompt = self._build_code_prompt(spec, test_code)
        code = self._call_llm(prompt)
        return self._clean_code(code)
    
    def _build_code_prompt(self, spec: CapabilitySpec, test_code: Optional[str] = None) -> str:
        """Build prompt for code generation"""
        spec_dict = spec.model_dump(mode='json')
        
        # Extract key information for prompt
        capability_id = spec.id
        operation_type = spec.operation_type.value
        risk_level = spec.risk.level.value
        has_undo = spec.compensation.supported
        parameters = [p.name for p in spec.parameters]
        returns = spec.returns or {}
        
        test_section = ""
        if test_code:
            test_section = f"""
**Test-Driven Development Mode:**
The following test code has been generated first. Your handler implementation MUST satisfy these tests:

```python
{test_code}
```

**Important:** Your handler code must pass all the tests above. Make sure:
- All test cases can pass
- Function signatures match test expectations
- Return values match test assertions
"""
        
        return f"""You are a Python code generator for AI-First Runtime handlers.
{test_section}

Generate a complete Python handler class for the following capability specification:

**Capability ID:** {capability_id}
**Operation Type:** {operation_type}
**Risk Level:** {risk_level}
**Supports Undo:** {has_undo}
**Parameters:** {', '.join(parameters)}
**Returns:** {json.dumps(returns, indent=2)}

**Full Spec (JSON):**
{json.dumps(spec_dict, indent=2)}

**Requirements:**
1. Create a class that inherits from `ActionHandler`
2. Implement the `execute` method with signature: `execute(self, params: Dict[str, Any], context: Any) -> ActionOutput`
3. Import necessary modules (e.g., `httpx` for network, `pathlib` for filesystem)
4. Use proper type hints for everything
5. Handle errors gracefully with try/except
6. Return `ActionOutput` with:
   - `result`: Dictionary matching the returns schema
   - `description`: Human-readable description of what was done
   - `undo_closure`: Optional callable function to reverse the operation (if has_undo=True)
7. If undo is supported, create a closure that captures all necessary state
8. Validate parameters before execution
9. Use the context parameter for workspace_root and other context info

**Example Structure:**
```python
from typing import Dict, Any, Optional, Callable
from pathlib import Path
from runtime.handler import ActionHandler
from runtime.types import ActionOutput

class {self._class_name_from_id(capability_id)}(ActionHandler):
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        # Validate parameters
        self.validate_params(params)
        
        # Extract parameters
        # ... your code here ...
        
        # Execute the operation
        # ... your code here ...
        
        # Create undo closure if needed
        def undo_closure() -> None:
            # ... undo logic here ...
            pass
        
        return ActionOutput(
            result={{...}},
            description="...",
            undo_closure=undo_closure if {str(has_undo).lower()} else None
        )
```

**Important:**
- Use `httpx` or `requests` for network operations
- Use `pathlib.Path` for filesystem operations
- Access workspace via `context.workspace_root` if needed
- For network operations, handle timeouts and errors
- For read operations, undo_closure should be None
- Make the code production-ready with proper error handling

Output ONLY the Python code, no explanations or markdown code blocks.
"""
    
    def _call_llm(self, prompt: str) -> str:
        """Call LLM to generate code"""
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
                {"role": "system", "content": "You are a Python code generator. Output only valid Python code, no markdown or explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return response.choices[0].message.content
    
    def _clean_code(self, code: str) -> str:
        """Clean generated code (remove markdown if present)"""
        # Remove markdown code blocks if present
        if code.startswith("```python"):
            code = code[9:]  # Remove ```python
        elif code.startswith("```"):
            code = code[3:]  # Remove ```
        
        if code.endswith("```"):
            code = code[:-3]  # Remove closing ```
        
        return code.strip()
    
    def _class_name_from_id(self, capability_id: str) -> str:
        """Convert capability ID to class name"""
        # e.g., "net.crypto.get_price" -> "GetPriceHandler"
        parts = capability_id.split(".")
        last_part = parts[-1]
        # Convert snake_case to PascalCase
        words = last_part.split("_")
        class_name = "".join(word.capitalize() for word in words) + "Handler"
        return class_name
