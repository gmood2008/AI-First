"""
OpenAI Function Adapter

Converts OpenAI Function Calling definitions into AI-First capabilities.
"""

import os
from typing import Dict, Any
from openai import OpenAI
import httpx

from .base import ExternalCapabilityAdapter
from ..handler import ActionHandler
from ..types import ActionOutput, ExecutionContext


class OpenAIFunctionAdapter(ExternalCapabilityAdapter):
    """
    Adapter for OpenAI Functions.
    
    Converts OpenAI Function Calling definitions into AI-First ActionHandler instances.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.function_name = config.get("function_name")
        if not self.function_name:
            raise ValueError("OpenAI Function adapter requires 'function_name' in config")
        
        # OpenAI API configuration
        self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or provide 'api_key' in config"
            )
        
        self.client = OpenAI(api_key=self.api_key)
        self.function_definition = config.get("function_definition", {})
        # Optional: HTTP endpoint to invoke the function (e.g. custom server)
        self.endpoint_url = config.get("endpoint_url")
        self.timeout = config.get("timeout", self.timeout or 30.0)
    
    def create_handler(self, spec_dict: Dict[str, Any]) -> ActionHandler:
        """Create a Handler that wraps OpenAI Function execution"""
        adapter = self
        
        class OpenAIFunctionHandler(ActionHandler):
            def __init__(self, spec):
                super().__init__(spec)
                self.adapter = adapter
            
            def execute(
                self,
                params: Dict[str, Any],
                context: ExecutionContext
            ) -> ActionOutput:
                """Execute OpenAI Function"""
                try:
                    # Convert params
                    function_params = adapter.convert_params(params)
                    
                    # Call function (this is a placeholder - actual implementation
                    # depends on how the function is exposed)
                    result = adapter._call_function(function_params)
                    
                    # Convert outputs
                    outputs = adapter.convert_outputs(result)
                    
                    description = f"Executed OpenAI Function: {adapter.function_name}"
                    
                    def undo_closure() -> None:
                        pass
                    
                    return ActionOutput(
                        result=outputs,
                        description=description,
                        undo_closure=undo_closure if adapter.supports_undo() else None
                    )
                
                except Exception as e:
                    raise RuntimeError(f"Failed to execute OpenAI Function: {e}") from e
        
        return OpenAIFunctionHandler(spec_dict)
    
    def convert_params(self, ai_first_params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert AI-First parameters to OpenAI Function format"""
        return ai_first_params.copy()
    
    def convert_outputs(self, external_response: Any) -> Dict[str, Any]:
        """Convert OpenAI Function response to AI-First format"""
        if isinstance(external_response, dict):
            return external_response
        elif isinstance(external_response, str):
            return {"result": external_response}
        else:
            return {"result": str(external_response)}
    
    def _call_function(self, params: Dict[str, Any]) -> Any:
        """
        Call the OpenAI Function.

        If config provides endpoint_url, invokes via HTTP POST (JSON body).
        Otherwise the caller must subclass and override, or use another adapter.
        """
        if self.endpoint_url:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.endpoint_url,
                    json=params,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                return response.json() if response.content else {}
        raise NotImplementedError(
            "OpenAI Function calling requires 'endpoint_url' in config, or "
            "subclass OpenAIFunctionAdapter and override _call_function()."
        )
