"""
LLM Client - Unified client for different LLM providers.

Supports OpenAI and DeepSeek APIs with compatible interface.
"""

import os
from typing import Optional
from openai import OpenAI


class LLMClient:
    """
    Unified LLM client that supports multiple providers.
    
    Currently supports:
    - OpenAI (default)
    - DeepSeek
    """
    
    def __init__(
        self,
        provider: str = "auto",
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: Provider name ("openai", "deepseek", or "auto" for auto-detect)
            model: Model name (e.g., "gpt-4o-mini", "deepseek-chat")
            api_key: API key (if None, will try to get from environment)
            base_url: Base URL for API (if None, will use default for provider)
        """
        self.provider = provider
        self.model = model
        self._client = None
        self._api_key = api_key
        self._base_url = base_url
    
    @property
    def client(self) -> OpenAI:
        """Get or create OpenAI-compatible client"""
        if self._client is None:
            # Auto-detect provider if needed
            if self.provider == "auto":
                self.provider = self._detect_provider()
            
            # Get API key
            api_key = self._api_key or self._get_api_key()
            
            # Get base URL
            base_url = self._base_url or self._get_base_url()
            
            # Create client
            self._client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
        
        return self._client
    
    def _detect_provider(self) -> str:
        """Auto-detect provider from environment variables"""
        # Check for DeepSeek API key first
        if os.getenv("DEEPSEEK_API_KEY"):
            return "deepseek"
        # Check for OpenAI API key
        elif os.getenv("OPENAI_API_KEY"):
            return "openai"
        else:
            # Default to OpenAI if no key found
            return "openai"
    
    def _get_api_key(self) -> str:
        """Get API key from environment"""
        if self.provider == "deepseek":
            key = os.getenv("DEEPSEEK_API_KEY")
            if not key:
                raise ValueError(
                    "DEEPSEEK_API_KEY not set. "
                    "Please set it with: export DEEPSEEK_API_KEY=your_key_here"
                )
            return key
        else:  # openai
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError(
                    "OPENAI_API_KEY not set. "
                    "Please set it with: export OPENAI_API_KEY=your_key_here"
                )
            return key
    
    def _get_base_url(self) -> Optional[str]:
        """Get base URL for provider"""
        if self.provider == "deepseek":
            return "https://api.deepseek.com/v1"
        else:  # openai
            return None  # Use default OpenAI URL
    
    def get_model_name(self) -> str:
        """Get the actual model name to use"""
        if self.provider == "deepseek":
            # Map common OpenAI model names to DeepSeek equivalents
            model_map = {
                "gpt-4o-mini": "deepseek-chat",
                "gpt-4o": "deepseek-chat",
                "gpt-4": "deepseek-chat",
                "gpt-3.5-turbo": "deepseek-chat",
            }
            return model_map.get(self.model, "deepseek-chat")
        else:
            return self.model


def create_llm_client(
    provider: str = "auto",
    model: str = "gpt-4o-mini",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None
) -> LLMClient:
    """
    Factory function to create LLM client.
    
    Args:
        provider: Provider name ("openai", "deepseek", or "auto")
        model: Model name
        api_key: Optional API key
        base_url: Optional base URL
    
    Returns:
        LLMClient instance
    """
    return LLMClient(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url
    )
