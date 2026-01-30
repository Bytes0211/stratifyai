"""Grok (X.AI) provider implementation."""

import os
from typing import Optional

from ..config import GROK_MODELS, PROVIDER_BASE_URLS
from ..exceptions import AuthenticationError
from .openai_compatible import OpenAICompatibleProvider


class GrokProvider(OpenAICompatibleProvider):
    """Grok (X.AI) provider using OpenAI-compatible API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: dict = None
    ):
        """
        Initialize Grok provider.
        
        Args:
            api_key: Grok API key (defaults to GROK_API_KEY env var)
            config: Optional provider-specific configuration
            
        Raises:
            AuthenticationError: If API key not provided
        """
        api_key = api_key or os.getenv("GROK_API_KEY")
        if not api_key:
            raise AuthenticationError("grok")
        
        base_url = PROVIDER_BASE_URLS["grok"]
        super().__init__(api_key, base_url, GROK_MODELS, config)
    
    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "grok"
