"""OpenRouter provider implementation."""

import os
from typing import Optional

from ..config import OPENROUTER_MODELS, PROVIDER_BASE_URLS
from ..exceptions import AuthenticationError
from .openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter provider using OpenAI-compatible API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: dict = None
    ):
        """
        Initialize OpenRouter provider.
        
        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            config: Optional provider-specific configuration
            
        Raises:
            AuthenticationError: If API key not provided
        """
        api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise AuthenticationError("openrouter")
        
        base_url = PROVIDER_BASE_URLS["openrouter"]
        super().__init__(api_key, base_url, OPENROUTER_MODELS, config)
    
    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "openrouter"
