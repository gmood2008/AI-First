"""
Claude Skill Adapter

Converts Claude Skills into AI-First capabilities.
"""

import os
import httpx
from typing import Dict, Any, Optional
import json

from .base import ExternalCapabilityAdapter
from ..handler import ActionHandler
from ..types import ActionOutput, ExecutionContext


class ClaudeSkillAdapter(ExternalCapabilityAdapter):
    """
    Adapter for Claude Skills.
    
    Converts Claude Skill API calls into AI-First ActionHandler instances.
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.skill_id = config.get("skill_id")
        if not self.skill_id:
            raise ValueError("Claude Skill adapter requires 'skill_id' in config")
        
        # Claude API configuration
        self.api_key = self.api_key or os.getenv("CLAUDE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Claude API key required. Set CLAUDE_API_KEY environment variable "
                "or provide 'api_key' in config"
            )
        
        self.base_url = self.base_url or "https://api.anthropic.com/v1"
        self.skill_endpoint = f"{self.base_url}/skills/{self.skill_id}/execute"
    
    def create_handler(self, spec_dict: Dict[str, Any]) -> ActionHandler:
        """
        Create a Handler that wraps Claude Skill execution.
        
        Args:
            spec_dict: AI-First capability specification
        
        Returns:
            ActionHandler instance
        """
        adapter = self  # Capture self in closure
        
        class ClaudeSkillHandler(ActionHandler):
            def __init__(self, spec):
                super().__init__(spec)
                self.adapter = adapter
            
            def execute(
                self, 
                params: Dict[str, Any], 
                context: ExecutionContext
            ) -> ActionOutput:
                """Execute Claude Skill"""
                try:
                    # Convert AI-First params to Claude Skill format
                    skill_params = adapter.convert_params(params)
                    
                    # Call Claude Skill API
                    response = adapter._call_skill_api(skill_params)
                    
                    # Convert response to AI-First format
                    outputs = adapter.convert_outputs(response)
                    
                    description = f"Executed Claude Skill: {adapter.skill_id}"
                    
                    # Create undo closure (if supported)
                    def undo_closure() -> None:
                        # Most external capabilities don't support undo
                        pass
                    
                    return ActionOutput(
                        result=outputs,
                        description=description,
                        undo_closure=undo_closure if adapter.supports_undo() else None
                    )
                
                except Exception as e:
                    raise RuntimeError(f"Failed to execute Claude Skill: {e}") from e
        
        return ClaudeSkillHandler(spec_dict)
    
    def convert_params(self, ai_first_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert AI-First parameters to Claude Skill format.
        
        Claude Skills typically accept parameters as a flat dictionary.
        """
        # For most cases, parameters can be passed directly
        # Override this method for custom parameter mapping
        return ai_first_params.copy()
    
    def convert_outputs(self, external_response: Any) -> Dict[str, Any]:
        """
        Convert Claude Skill response to AI-First output format.
        
        Args:
            external_response: Response from Claude Skill API
        
        Returns:
            Dictionary with AI-First output format
        """
        # Handle different response formats
        if isinstance(external_response, dict):
            # If response has a 'result' or 'output' key, extract it
            if "result" in external_response:
                return {"result": external_response["result"]}
            elif "output" in external_response:
                return {"result": external_response["output"]}
            else:
                # Return the entire response
                return {"result": external_response}
        elif isinstance(external_response, str):
            return {"result": external_response}
        else:
            return {"result": str(external_response)}
    
    def _call_skill_api(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Claude Skill API.
        
        Args:
            params: Parameters for the skill
        
        Returns:
            API response
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "parameters": params
        }
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    self.skill_endpoint,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPError as e:
            raise RuntimeError(f"Claude Skill API error: {e}") from e
