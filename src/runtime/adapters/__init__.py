"""
External Capability Adapters

This module provides adapters for integrating third-party capabilities
(Claude Skills, OpenAI Functions, LangChain Tools, etc.) into AI-First Runtime.
"""

from .base import ExternalCapabilityAdapter, AdapterConfig
from .claude_skill import ClaudeSkillAdapter
from .openai_function import OpenAIFunctionAdapter
from .http_api import HTTPAPIAdapter

__all__ = [
    "ExternalCapabilityAdapter",
    "AdapterConfig",
    "ClaudeSkillAdapter",
    "OpenAIFunctionAdapter",
    "HTTPAPIAdapter",
    "create_adapter",
]


def create_adapter(adapter_type: str, config: dict) -> ExternalCapabilityAdapter:
    """
    Factory function to create an adapter instance.
    
    Args:
        adapter_type: Type of adapter ("claude_skill", "openai_function", "http_api")
        config: Adapter configuration dictionary
    
    Returns:
        Adapter instance
    
    Raises:
        ValueError: If adapter_type is not supported
    """
    if adapter_type == "claude_skill":
        return ClaudeSkillAdapter(config)
    elif adapter_type == "openai_function":
        return OpenAIFunctionAdapter(config)
    elif adapter_type == "http_api":
        return HTTPAPIAdapter(config)
    else:
        raise ValueError(
            f"Unsupported adapter type: {adapter_type}. "
            f"Supported types: claude_skill, openai_function, http_api"
        )
