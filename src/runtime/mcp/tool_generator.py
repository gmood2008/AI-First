"""
Dynamic Tool Generator - Create FastMCP-compatible tool functions.

This module generates Python functions with explicit parameter signatures
from MCP tool definitions, allowing FastMCP to properly introspect them.
"""

import json
from typing import Dict, Any, Callable, get_type_hints
from inspect import Parameter, Signature


def create_tool_function(
    capability_id: str,
    tool_def: Dict[str, Any],
    execute_callback: Callable,
) -> Callable:
    """
    Create a FastMCP-compatible tool function.
    
    This function dynamically generates a Python function with:
    - Explicit parameter signatures (no **kwargs)
    - Type hints
    - Docstring
    
    Args:
        capability_id: AI-First capability ID
        tool_def: MCP tool definition
        execute_callback: Async function to call for execution
    
    Returns:
        Async function compatible with FastMCP @tool decorator
    """
    # Extract input schema
    input_schema = tool_def.get("inputSchema", {})
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))
    
    # Build parameter list
    params = []
    param_types = {}
    
    for param_name, param_schema in properties.items():
        # Map JSON Schema types to Python types
        param_type = _json_type_to_python(param_schema.get("type", "string"))
        param_types[param_name] = param_type
        
        # Create parameter
        if param_name in required:
            # Required parameter
            params.append(
                Parameter(
                    param_name,
                    Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=param_type,
                )
            )
        else:
            # Optional parameter with default None
            params.append(
                Parameter(
                    param_name,
                    Parameter.POSITIONAL_OR_KEYWORD,
                    default=None,
                    annotation=param_type | None,
                )
            )
    
    # Create function signature
    signature = Signature(params, return_annotation=str)
    
    # Create function
    async def tool_func(*args, **kwargs):
        """Dynamic tool function"""
        # Build params dict
        params_dict = {}
        
        # Handle positional args
        for i, arg in enumerate(args):
            if i < len(params):
                params_dict[params[i].name] = arg
        
        # Handle keyword args
        params_dict.update(kwargs)
        
        # Remove None values for optional parameters
        params_dict = {k: v for k, v in params_dict.items() if v is not None}
        
        # Execute capability
        try:
            result = await execute_callback(capability_id, params_dict)
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__,
            }, indent=2)
    
    # Set function metadata
    tool_func.__name__ = capability_id.replace(".", "_")
    tool_func.__doc__ = tool_def.get("description", "")
    tool_func.__signature__ = signature
    
    return tool_func


def _json_type_to_python(json_type: str) -> type:
    """
    Map JSON Schema type to Python type.
    
    Args:
        json_type: JSON Schema type string
    
    Returns:
        Python type
    """
    type_map = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
        "null": type(None),
    }
    
    return type_map.get(json_type, str)
