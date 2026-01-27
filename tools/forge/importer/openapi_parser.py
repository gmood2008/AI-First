"""
OpenAPI/Swagger specification parser.
"""

import yaml
import json
from typing import List, Dict, Any, Optional
from pathlib import Path

from .types import EndpointInfo, ParameterInfo, SideEffectType


class OpenAPIParser:
    """Parse OpenAPI/Swagger specifications"""
    
    # HTTP method to side effect mapping
    METHOD_SIDE_EFFECTS = {
        "GET": ["network_read"],
        "POST": ["network_write", "state_mutation"],
        "PUT": ["network_write", "state_mutation"],
        "PATCH": ["network_write", "state_mutation"],
        "DELETE": ["network_write", "state_mutation"],
        "HEAD": ["network_read"],
        "OPTIONS": ["network_read"],
    }
    
    def parse_file(self, file_path: str, endpoint_path: Optional[str] = None, method: Optional[str] = None) -> List[EndpointInfo]:
        """
        Parse OpenAPI spec file and extract endpoint information.
        
        Args:
            file_path: Path to OpenAPI YAML/JSON file
            endpoint_path: Specific endpoint path to extract (None = all endpoints)
            method: Specific HTTP method to extract (None = all methods)
        
        Returns:
            List of EndpointInfo objects
        """
        file_path_obj = Path(file_path)
        
        with open(file_path, 'r') as f:
            if file_path_obj.suffix in ['.yaml', '.yml']:
                spec = yaml.safe_load(f)
            elif file_path_obj.suffix == '.json':
                spec = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {file_path_obj.suffix}")
        
        return self.parse_spec(spec, endpoint_path, method)
    
    def parse_spec(self, spec: Dict[str, Any], endpoint_path: Optional[str] = None, method: Optional[str] = None) -> List[EndpointInfo]:
        """
        Parse OpenAPI spec dictionary and extract endpoint information.
        
        Args:
            spec: OpenAPI specification dictionary
            endpoint_path: Specific endpoint path to extract (None = all endpoints)
            method: Specific HTTP method to extract (None = all methods)
        
        Returns:
            List of EndpointInfo objects
        """
        if "paths" not in spec:
            raise ValueError("Invalid OpenAPI spec: missing 'paths' field")
        
        endpoints = []
        paths = spec["paths"]
        
        for path, path_item in paths.items():
            if endpoint_path and path != endpoint_path:
                continue
            
            for http_method, operation in path_item.items():
                if http_method.upper() not in self.METHOD_SIDE_EFFECTS:
                    continue  # Skip non-HTTP method keys (like 'parameters', 'summary')
                
                if method and http_method.upper() != method.upper():
                    continue
                
                endpoint_info = self._extract_endpoint_info(path, http_method.upper(), operation, spec)
                endpoints.append(endpoint_info)
        
        if not endpoints:
            if endpoint_path and method:
                raise ValueError(f"Endpoint '{method} {endpoint_path}' not found in spec")
            elif endpoint_path:
                raise ValueError(f"Endpoint path '{endpoint_path}' not found in spec")
            else:
                raise ValueError("No endpoints found in spec")
        
        return endpoints
    
    def _extract_endpoint_info(self, path: str, method: str, operation: Dict[str, Any], spec: Dict[str, Any]) -> EndpointInfo:
        """Extract information from an OpenAPI operation"""
        return EndpointInfo(
            path=path,
            method=method,
            summary=operation.get("summary", ""),
            description=operation.get("description", ""),
            parameters=self._extract_parameters(operation, spec),
            responses=operation.get("responses", {}),
            side_effects=self.METHOD_SIDE_EFFECTS.get(method, []),
            tags=operation.get("tags", []),
        )
    
    def _extract_parameters(self, operation: Dict[str, Any], spec: Dict[str, Any]) -> List[ParameterInfo]:
        """Extract parameter information from operation"""
        params = []
        
        # Extract from 'parameters' field
        for param in operation.get("parameters", []):
            param_info = self._parse_parameter(param, spec)
            if param_info:
                params.append(param_info)
        
        # Extract from 'requestBody' field (OpenAPI 3.0)
        if "requestBody" in operation:
            body_params = self._extract_request_body_params(operation["requestBody"], spec)
            params.extend(body_params)
        
        return params
    
    def _parse_parameter(self, param: Dict[str, Any], spec: Dict[str, Any]) -> Optional[ParameterInfo]:
        """Parse a single parameter definition"""
        # Handle $ref
        if "$ref" in param:
            param = self._resolve_ref(param["$ref"], spec)
        
        name = param.get("name", "unknown")
        schema = param.get("schema", {})
        
        # Handle $ref in schema
        if "$ref" in schema:
            schema = self._resolve_ref(schema["$ref"], spec)
        
        param_type = self._map_openapi_type(schema.get("type", "string"))
        description = param.get("description", schema.get("description", f"Parameter {name}"))
        required = param.get("required", False)
        
        return ParameterInfo(
            name=name,
            type=param_type,
            description=description,
            required=required,
            sensitive=self._is_sensitive_param(name),
        )
    
    def _extract_request_body_params(self, request_body: Dict[str, Any], spec: Dict[str, Any]) -> List[ParameterInfo]:
        """Extract parameters from requestBody (OpenAPI 3.0)"""
        params = []
        
        # Handle $ref
        if "$ref" in request_body:
            request_body = self._resolve_ref(request_body["$ref"], spec)
        
        content = request_body.get("content", {})
        
        # Try to find JSON content
        for content_type in ["application/json", "application/x-www-form-urlencoded", "*/*"]:
            if content_type in content:
                schema = content[content_type].get("schema", {})
                
                # Handle $ref in schema
                if "$ref" in schema:
                    schema = self._resolve_ref(schema["$ref"], spec)
                
                # Extract properties from schema
                if "properties" in schema:
                    required_fields = schema.get("required", [])
                    for prop_name, prop_schema in schema["properties"].items():
                        param_type = self._map_openapi_type(prop_schema.get("type", "string"))
                        description = prop_schema.get("description", f"Parameter {prop_name}")
                        
                        params.append(ParameterInfo(
                            name=prop_name,
                            type=param_type,
                            description=description,
                            required=prop_name in required_fields,
                            sensitive=self._is_sensitive_param(prop_name),
                        ))
                break
        
        return params
    
    def _resolve_ref(self, ref: str, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a $ref pointer"""
        # Remove leading '#/'
        if ref.startswith("#/"):
            ref = ref[2:]
        
        parts = ref.split("/")
        current = spec
        
        for part in parts:
            if part in current:
                current = current[part]
            else:
                return {}
        
        return current
    
    def _map_openapi_type(self, openapi_type: str) -> str:
        """Map OpenAPI type to AI-First type"""
        type_map = {
            "string": "string",
            "integer": "integer",
            "number": "float",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
        }
        return type_map.get(openapi_type, "string")
    
    def _is_sensitive_param(self, param_name: str) -> bool:
        """Check if parameter name suggests sensitive data"""
        sensitive_keywords = ["token", "key", "secret", "password", "credential", "auth", "api_key", "apikey"]
        return any(keyword in param_name.lower() for keyword in sensitive_keywords)
