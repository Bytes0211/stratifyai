"""Groq provider implementation."""

import os
from typing import Optional

from ..config import GROQ_MODELS, PROVIDER_BASE_URLS
from ..exceptions import AuthenticationError
from .openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    """Groq provider using OpenAI-compatible API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: dict = None
    ):
        """
        Initialize Groq provider.
        
        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            config: Optional provider-specific configuration
            
        Raises:
            AuthenticationError: If API key not provided
        """
        api_key = api_key or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise AuthenticationError("groq")
        
        base_url = PROVIDER_BASE_URLS["groq"]
        super().__init__(api_key, base_url, GROQ_MODELS, config)
    
    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "groq"
