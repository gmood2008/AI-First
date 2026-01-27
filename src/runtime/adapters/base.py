"""
Base Adapter for External Capabilities

Defines the interface for all external capability adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..handler import ActionHandler
from ..types import ActionOutput, ExecutionContext


@dataclass
class AdapterConfig:
    """Configuration for external capability adapters"""
    adapter_type: str
    capability_id: str
    api_key: Optional[str] = None
    api_key_env: Optional[str] = None
    base_url: Optional[str] = None
    timeout: float = 30.0
    extra_params: Optional[Dict[str, Any]] = None


class ExternalCapabilityAdapter(ABC):
    """
    Base class for external capability adapters.
    
    Adapters convert external capabilities (Claude Skills, OpenAI Functions, etc.)
    into AI-First ActionHandler instances.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter.
        
        Args:
            config: Adapter configuration dictionary
        """
        self.config = config
        self.capability_id = config.get("capability_id", "unknown")
        self.api_key = self._get_api_key(config)
        self.base_url = config.get("base_url")
        self.timeout = config.get("timeout", 30.0)
    
    def _get_api_key(self, config: Dict[str, Any]) -> Optional[str]:
        """Get API key from config or environment variable"""
        import os
        
        # Direct API key
        if "api_key" in config:
            return config["api_key"]
        
        # Environment variable
        if "api_key_env" in config:
            return os.getenv(config["api_key_env"])
        
        return None
    
    @abstractmethod
    def create_handler(self, spec_dict: Dict[str, Any]) -> ActionHandler:
        """
        Create an ActionHandler that wraps the external capability.
        
        Args:
            spec_dict: AI-First capability specification
        
        Returns:
            ActionHandler instance that calls the external capability
        """
        pass
    
    @abstractmethod
    def convert_params(self, ai_first_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert AI-First parameter format to external API format.
        
        Args:
            ai_first_params: Parameters in AI-First format
        
        Returns:
            Parameters in external API format
        """
        pass
    
    @abstractmethod
    def convert_outputs(self, external_response: Any) -> Dict[str, Any]:
        """
        Convert external API response to AI-First output format.
        
        Args:
            external_response: Response from external API
        
        Returns:
            Outputs in AI-First format
        """
        pass
    
    def supports_undo(self) -> bool:
        """
        Check if the external capability supports undo operations.
        
        Returns:
            True if undo is supported, False otherwise
        """
        return False  # Most external capabilities don't support undo
