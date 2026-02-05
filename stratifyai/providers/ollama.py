"""Ollama provider implementation for local models."""

import os
from typing import Optional

from ..config import OLLAMA_MODELS, PROVIDER_BASE_URLS
from .openai_compatible import OpenAICompatibleProvider


class OllamaProvider(OpenAICompatibleProvider):
    """Ollama provider for local models using OpenAI-compatible API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: dict = None
    ):
        """
        Initialize Ollama provider.
        
        Args:
            api_key: Optional API key (Ollama typically doesn't require one)
            config: Optional provider-specific configuration (can include base_url)
            
        Note:
            Ollama runs locally and typically doesn't require an API key.
            Default base URL is http://localhost:11434/v1
        """
        # Ollama doesn't require an API key, use placeholder
        from ..api_key_helper import APIKeyHelper
        api_key = APIKeyHelper.get_api_key("ollama", api_key) or "ollama"
        
        # Allow custom base URL via config
        base_url = PROVIDER_BASE_URLS["ollama"]
        if config and "base_url" in config:
            base_url = config["base_url"]
        
        super().__init__(api_key, base_url, OLLAMA_MODELS, config)
    
    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "ollama"
