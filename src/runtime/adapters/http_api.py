"""
HTTP API Adapter

Generic adapter for HTTP-based external capabilities.
"""

import httpx
from typing import Dict, Any, Optional

from .base import ExternalCapabilityAdapter
from ..handler import ActionHandler
from ..types import ActionOutput, ExecutionContext


class HTTPAPIAdapter(ExternalCapabilityAdapter):
    """
    Generic HTTP API adapter.
    
    Converts any HTTP API endpoint into an AI-First capability.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.endpoint_url = config.get("endpoint_url")
        if not self.endpoint_url:
            raise ValueError("HTTP API adapter requires 'endpoint_url' in config")
        
        self.method = config.get("method", "POST").upper()
        self.headers = config.get("headers", {})
        self.auth_type = config.get("auth_type", "none")  # none, bearer, api_key, basic
        self.auth_config = config.get("auth_config", {})
    
    def create_handler(self, spec_dict: Dict[str, Any]) -> ActionHandler:
        """Create a Handler that wraps HTTP API calls"""
        adapter = self
        
        class HTTPAPIHandler(ActionHandler):
            def __init__(self, spec):
                super().__init__(spec)
                self.adapter = adapter
            
            def execute(
                self,
                params: Dict[str, Any],
                context: ExecutionContext
            ) -> ActionOutput:
                """Execute HTTP API call"""
                try:
                    # Convert params
                    api_params = adapter.convert_params(params)
                    
                    # Make HTTP request
                    response = adapter._make_request(api_params)
                    
                    # Convert outputs
                    outputs = adapter.convert_outputs(response)
                    
                    description = f"Executed HTTP API: {adapter.method} {adapter.endpoint_url}"
                    
                    def undo_closure() -> None:
                        pass
                    
                    return ActionOutput(
                        result=outputs,
                        description=description,
                        undo_closure=undo_closure if adapter.supports_undo() else None
                    )
                
                except Exception as e:
                    raise RuntimeError(f"Failed to execute HTTP API: {e}") from e
        
        return HTTPAPIHandler(spec_dict)
    
    def convert_params(self, ai_first_params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert AI-First parameters to HTTP API format"""
        # Default: pass params as JSON body for POST, query params for GET
        return ai_first_params.copy()
    
    def convert_outputs(self, external_response: Any) -> Dict[str, Any]:
        """Convert HTTP API response to AI-First format"""
        if isinstance(external_response, dict):
            return external_response
        elif isinstance(external_response, str):
            return {"result": external_response}
        else:
            return {"result": str(external_response)}
    
    def _make_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to the API endpoint"""
        headers = self.headers.copy()
        
        # Add authentication
        headers.update(self._get_auth_headers())
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                if self.method == "GET":
                    response = client.get(
                        self.endpoint_url,
                        headers=headers,
                        params=params
                    )
                elif self.method == "POST":
                    response = client.post(
                        self.endpoint_url,
                        headers=headers,
                        json=params
                    )
                elif self.method == "PUT":
                    response = client.put(
                        self.endpoint_url,
                        headers=headers,
                        json=params
                    )
                elif self.method == "DELETE":
                    response = client.delete(
                        self.endpoint_url,
                        headers=headers,
                        params=params
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {self.method}")
                
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP API error: {e}") from e
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth_type"""
        headers = {}
        
        if self.auth_type == "bearer":
            token = self.auth_config.get("token") or self.api_key
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        elif self.auth_type == "api_key":
            key_name = self.auth_config.get("key_name", "X-API-Key")
            key_value = self.auth_config.get("key_value") or self.api_key
            if key_value:
                headers[key_name] = key_value
        
        elif self.auth_type == "basic":
            # Basic auth would need username/password
            # This is a simplified version
            pass
        
        return headers
