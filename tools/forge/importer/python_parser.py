"""
Python code parser using AST analysis.
"""

import ast
import inspect
from typing import List, Optional, Any
from pathlib import Path

from .types import FunctionInfo, ParameterInfo, SideEffectType


class PythonParser:
    """Parse Python code to extract function information"""
    
    # Side effect detection patterns
    SIDE_EFFECT_PATTERNS = {
        # Filesystem operations
        "open": {"filesystem_write": ["'w'", "'a'", "'wb'", "'ab'"], "filesystem_read": ["'r'", "'rb'"]},
        "Path.write_text": ["filesystem_write"],
        "Path.write_bytes": ["filesystem_write"],
        "Path.read_text": ["filesystem_read"],
        "Path.read_bytes": ["filesystem_read"],
        "Path.unlink": ["filesystem_delete"],
        "Path.rmdir": ["filesystem_delete"],
        "os.remove": ["filesystem_delete"],
        "os.unlink": ["filesystem_delete"],
        "os.rmdir": ["filesystem_delete"],
        "shutil.move": ["filesystem_write"],
        "shutil.copy": ["filesystem_write"],
        "shutil.rmtree": ["filesystem_delete"],
        
        # Network operations
        "requests.get": ["network_read"],
        "requests.post": ["network_write"],
        "requests.put": ["network_write"],
        "requests.patch": ["network_write"],
        "requests.delete": ["network_write"],
        "urllib.request.urlopen": ["network_read"],
        "socket.connect": ["network_write"],
        "socket.send": ["network_write"],
        
        # System operations
        "subprocess.run": ["system_exec"],
        "subprocess.call": ["system_exec"],
        "subprocess.Popen": ["system_exec"],
        "os.system": ["system_exec"],
        "os.exec": ["system_exec"],
    }
    
    def parse_file(self, file_path: str, function_name: Optional[str] = None) -> List[FunctionInfo]:
        """
        Parse Python file and extract function information.
        
        Args:
            file_path: Path to Python file
            function_name: Specific function to extract (None = all functions)
        
        Returns:
            List of FunctionInfo objects
        """
        with open(file_path, 'r') as f:
            code = f.read()
        
        return self.parse_code(code, function_name, module_name=Path(file_path).stem)
    
    def parse_code(self, code: str, function_name: Optional[str] = None, module_name: Optional[str] = None) -> List[FunctionInfo]:
        """
        Parse Python code string and extract function information.
        
        Args:
            code: Python source code
            function_name: Specific function to extract (None = all functions)
            module_name: Name of the module (for reference)
        
        Returns:
            List of FunctionInfo objects
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid Python syntax: {e}")
        
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if function_name is None or node.name == function_name:
                    func_info = self._extract_function_info(node, code, module_name)
                    functions.append(func_info)
        
        if not functions:
            if function_name:
                raise ValueError(f"Function '{function_name}' not found in code")
            else:
                raise ValueError("No functions found in code")
        
        return functions
    
    def _extract_function_info(self, node: ast.FunctionDef, source_code: str, module_name: Optional[str]) -> FunctionInfo:
        """Extract information from a function AST node"""
        return FunctionInfo(
            name=node.name,
            docstring=ast.get_docstring(node) or "",
            parameters=self._extract_parameters(node),
            return_type=self._extract_return_type(node),
            side_effects=self._detect_side_effects(node),
            source_code=ast.get_source_segment(source_code, node) or "",
            module_name=module_name,
        )
    
    def _extract_parameters(self, node: ast.FunctionDef) -> List[ParameterInfo]:
        """Extract parameter information from function"""
        params = []
        args = node.args
        
        # Regular arguments
        for i, arg in enumerate(args.args):
            # Skip 'self' and 'cls'
            if arg.arg in ['self', 'cls']:
                continue
            
            param_type = self._get_annotation_type(arg.annotation)
            default_value = None
            required = True
            
            # Check if has default value
            default_offset = len(args.args) - len(args.defaults)
            if i >= default_offset:
                default_value = self._get_default_value(args.defaults[i - default_offset])
                required = False
            
            params.append(ParameterInfo(
                name=arg.arg,
                type=param_type,
                description=f"Parameter {arg.arg}",  # Will be improved by LLM
                required=required,
                default=default_value,
                sensitive=self._is_sensitive_param(arg.arg),
            ))
        
        return params
    
    def _get_annotation_type(self, annotation: Optional[ast.expr]) -> str:
        """Extract type from annotation"""
        if annotation is None:
            return "string"  # Default type
        
        if isinstance(annotation, ast.Name):
            type_map = {
                "str": "string",
                "int": "integer",
                "float": "float",
                "bool": "boolean",
                "list": "array",
                "dict": "object",
            }
            return type_map.get(annotation.id, "string")
        
        if isinstance(annotation, ast.Subscript):
            # Handle List[str], Dict[str, int], etc.
            if isinstance(annotation.value, ast.Name):
                base_type = annotation.value.id
                if base_type in ["List", "list"]:
                    return "array"
                elif base_type in ["Dict", "dict"]:
                    return "object"
        
        return "string"
    
    def _get_default_value(self, node: ast.expr) -> Any:
        """Extract default value from AST node"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            if node.id == "None":
                return None
            elif node.id == "True":
                return True
            elif node.id == "False":
                return False
        return None
    
    def _is_sensitive_param(self, param_name: str) -> bool:
        """Check if parameter name suggests sensitive data"""
        sensitive_keywords = ["token", "key", "secret", "password", "credential", "auth"]
        return any(keyword in param_name.lower() for keyword in sensitive_keywords)
    
    def _extract_return_type(self, node: ast.FunctionDef) -> str:
        """Extract return type from function"""
        if node.returns:
            return self._get_annotation_type(node.returns)
        return "object"  # Default return type
    
    def _detect_side_effects(self, node: ast.FunctionDef) -> List[SideEffectType]:
        """Detect side effects by analyzing function body"""
        side_effects = set()
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child)
                
                # Check against known patterns
                for pattern, effects in self.SIDE_EFFECT_PATTERNS.items():
                    if isinstance(effects, dict):
                        # Special handling for open() with mode argument
                        if pattern in call_name and "open" in pattern:
                            mode = self._get_open_mode(child)
                            for mode_pattern, effect_list in effects.items():
                                if mode and mode_pattern in mode:
                                    side_effects.update(effect_list)
                    elif isinstance(effects, list):
                        if pattern in call_name:
                            side_effects.update(effects)
        
        return sorted(list(side_effects))
    
    def _get_call_name(self, node: ast.Call) -> str:
        """Get the full name of a function call"""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""
    
    def _get_open_mode(self, node: ast.Call) -> Optional[str]:
        """Extract mode argument from open() call"""
        # Check keyword arguments
        for keyword in node.keywords:
            if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
                return repr(keyword.value.value)
        
        # Check positional arguments (mode is second arg)
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
            return repr(node.args[1].value)
        
        return None
