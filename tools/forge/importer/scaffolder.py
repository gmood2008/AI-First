"""
Handler code scaffolder - generates Python handler code from specs.
"""

from pathlib import Path
from typing import Optional
from .types import CapabilitySpec, FunctionInfo


class HandlerScaffolder:
    """Generate Python handler code from capability specifications"""
    
    def generate_handler(self, spec: CapabilitySpec, func_info: Optional[FunctionInfo] = None) -> str:
        """
        Generate handler Python code.
        
        Args:
            spec: Capability specification
            func_info: Optional original function info (for wrapping existing code)
        
        Returns:
            Generated Python code
        """
        class_name = self._spec_id_to_class_name(spec.meta.id)
        
        # Extract parameter names
        param_names = list(spec.interface.inputs.keys())
        
        # Determine if has side effects
        has_side_effects = len(spec.contracts.side_effects) > 0
        has_write_effects = any(
            effect in ["filesystem_write", "filesystem_delete", "network_write", "system_exec", "state_mutation"]
            for effect in spec.contracts.side_effects
        )
        
        # Build parameter extraction code
        param_extraction = self._generate_param_extraction(spec)
        
        # Build operation logic (placeholder or wrapped function)
        if func_info:
            operation_logic = self._generate_wrapped_call(func_info, param_names)
        else:
            operation_logic = self._generate_placeholder_logic(spec)
        
        # Build undo logic
        undo_logic = self._generate_undo_logic(spec)
        
        # Build result dict
        result_dict = self._generate_result_dict(spec)
        
        # Generate imports
        imports = self._generate_imports(spec, func_info)
        
        # Build handler code
        code = f'''{imports}

class {class_name}Handler(ActionHandler):
    """Handler for {spec.meta.id}
    
    {spec.meta.description}
    """
    
    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        """Execute {spec.meta.id} capability"""
        # Extract parameters
{param_extraction}
        
        # TODO: Capture state for undo (if needed)
        # Example: file_existed = Path(file_path).exists()
        #          backup_content = Path(file_path).read_text() if file_existed else None
        
        # Execute operation
{operation_logic}
        
        # Create undo closure
{undo_logic}
        
        return ActionOutput(
            result={result_dict},
            undo_closure=undo if {str(has_write_effects)} else None,
            description="{spec.meta.description}"
        )
'''
        
        return code
    
    def generate_test(self, spec: CapabilitySpec) -> str:
        """
        Generate test code for handler.
        
        Args:
            spec: Capability specification
        
        Returns:
            Generated test code
        """
        class_name = self._spec_id_to_class_name(spec.meta.id)
        test_params = self._generate_test_params(spec)
        test_func_name = spec.meta.id.replace(".", "_")
        
        has_write_effects = any(
            effect in ["filesystem_write", "filesystem_delete", "network_write", "system_exec", "state_mutation"]
            for effect in spec.contracts.side_effects
        )
        
        # Build undo test section
        undo_test = ""
        if has_write_effects:
            undo_test = f'''\n\ndef test_{test_func_name}_undo(handler, context):
    """Test undo functionality"""
    params = {test_params}
    
    # Execute operation
    result = handler.execute(params, context)
    assert result.undo_closure is not None
    
    # TODO: Verify operation was performed
    
    # Execute undo
    result.undo_closure()
    
    # TODO: Verify operation was undone
'''
        
        code = f'''"""
Tests for {spec.meta.id} handler.
"""

import pytest
from pathlib import Path
from runtime.types import ExecutionContext
from runtime.handler import load_spec_from_yaml

# Import handler (adjust path as needed)
from .{spec.meta.id.replace(".", "_")}_handler import {class_name}Handler


@pytest.fixture
def handler():
    """Create handler instance"""
    # Load spec from YAML
    spec_path = Path(__file__).parent / "{spec.meta.id}.yaml"
    spec_dict = load_spec_from_yaml(spec_path)
    return {class_name}Handler(spec_dict)


@pytest.fixture
def context():
    """Create execution context"""
    return ExecutionContext(
        user_id="test_user",
        workspace_root="/tmp/test_workspace",
        session_id="test_session",
        confirmation_callback=lambda msg, params: True,
        undo_enabled=True,
        backup_dir="/tmp/test_backup",
    )


def test_{test_func_name}_basic(handler, context):
    """Test basic execution"""
    params = {test_params}
    
    result = handler.execute(params, context)
    
    assert result.result is not None
    # TODO: Add specific assertions based on expected outputs
    # assert result.result["success"] == True
    # assert result.result["output_field"] == expected_value
{undo_test}


def test_{test_func_name}_validation(handler, context):
    """Test parameter validation"""
    # Test with missing required parameter
    with pytest.raises(ValueError):
        handler.execute({{}}, context)
    
    # TODO: Add more validation tests
'''
        
        return code
    
    def _spec_id_to_class_name(self, spec_id: str) -> str:
        """Convert spec ID to PascalCase class name"""
        # io.fs.write_file -> WriteFile
        parts = spec_id.split(".")
        return "".join(word.capitalize() for word in parts[-1].split("_"))
    
    def _generate_imports(self, spec: CapabilitySpec, func_info: Optional[FunctionInfo]) -> str:
        """Generate import statements"""
        imports = [
            "from runtime.handler import ActionHandler",
            "from runtime.types import ActionOutput",
            "from typing import Dict, Any",
        ]
        
        # Add imports based on side effects
        if "filesystem_write" in spec.contracts.side_effects or "filesystem_read" in spec.contracts.side_effects:
            imports.append("from pathlib import Path")
        
        if "network_read" in spec.contracts.side_effects or "network_write" in spec.contracts.side_effects:
            imports.append("import requests")
        
        if "system_exec" in spec.contracts.side_effects:
            imports.append("import subprocess")
        
        # Add imports from original function
        if func_info and func_info.source_code:
            # Try to extract imports from source code
            for line in func_info.source_code.split("\n"):
                if line.strip().startswith("import ") or line.strip().startswith("from "):
                    if line not in imports:
                        imports.append(line.strip())
        
        return "\n".join(imports)
    
    def _generate_param_extraction(self, spec: CapabilitySpec) -> str:
        """Generate parameter extraction code"""
        lines = []
        for param_name, param in spec.interface.inputs.items():
            if param.required:
                lines.append(f'        {param_name} = params["{param_name}"]')
            else:
                default_repr = repr(param.default) if param.default is not None else "None"
                lines.append(f'        {param_name} = params.get("{param_name}", {default_repr})')
        return "\n".join(lines)
    
    def _generate_wrapped_call(self, func_info: FunctionInfo, param_names: list) -> str:
        """Generate code to call original function"""
        args_str = ", ".join([f"{name}={name}" for name in param_names])
        return f'''        # Call original function
        result = {func_info.name}({args_str})'''
    
    def _generate_placeholder_logic(self, spec: CapabilitySpec) -> str:
        """Generate placeholder operation logic"""
        return f'''        # TODO: Implement {spec.meta.id} logic here
        # This is a placeholder - replace with actual implementation
        result = {{"success": True}}'''
    
    def _generate_undo_logic(self, spec: CapabilitySpec) -> str:
        """Generate undo closure code"""
        has_write_effects = any(
            effect in ["filesystem_write", "filesystem_delete", "network_write", "system_exec", "state_mutation"]
            for effect in spec.contracts.side_effects
        )
        
        if not has_write_effects:
            return '''        # No undo needed (read-only operation)
        undo = None'''
        
        # Generate undo closure based on undo_strategy
        undo_strategy = spec.behavior.undo_strategy
        
        return f'''        def undo():
            """Undo {spec.meta.id}
            
            Strategy: {undo_strategy}
            """
            # TODO: Implement undo logic based on strategy
            # Example patterns:
            # - Delete created file: Path(file_path).unlink(missing_ok=True)
            # - Restore from backup: Path(file_path).write_text(backup_content)
            # - Reverse API call: requests.delete(f"{{api_url}}/{{resource_id}}")
            pass'''
    
    def _generate_result_dict(self, spec: CapabilitySpec) -> str:
        """Generate result dictionary code"""
        if not spec.interface.outputs:
            return '{"success": True}'
        
        # Generate dict with output fields
        fields = []
        for output_name in spec.interface.outputs.keys():
            fields.append(f'"{output_name}": result.get("{output_name}")')
        
        return "{\n            " + ",\n            ".join(fields) + "\n        }"
    
    def _generate_test_params(self, spec: CapabilitySpec) -> str:
        """Generate test parameter dictionary"""
        params = {}
        for param_name, param in spec.interface.inputs.items():
            if param.type == "string":
                params[param_name] = f"test_{param_name}"
            elif param.type == "integer":
                params[param_name] = 42
            elif param.type == "float":
                params[param_name] = 3.14
            elif param.type == "boolean":
                params[param_name] = True
            elif param.type == "array":
                params[param_name] = []
            elif param.type == "object":
                params[param_name] = {}
        
        return "{\n        " + ",\n        ".join([f'"{k}": {repr(v)}' for k, v in params.items()]) + "\n    }"
    
    def write_files(self, spec: CapabilitySpec, output_dir: Path, func_info: Optional[FunctionInfo] = None, generate_tests: bool = True):
        """
        Write handler and test files to disk.
        
        Args:
            spec: Capability specification
            output_dir: Output directory
            func_info: Optional original function info
            generate_tests: Whether to generate test file
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate handler file
        handler_code = self.generate_handler(spec, func_info)
        handler_file = output_dir / f"{spec.meta.id.replace('.', '_')}_handler.py"
        handler_file.write_text(handler_code)
        
        # Generate test file
        if generate_tests:
            test_code = self.generate_test(spec)
            test_file = output_dir / f"test_{spec.meta.id.replace('.', '_')}_handler.py"
            test_file.write_text(test_code)
        
        return handler_file, test_file if generate_tests else None
