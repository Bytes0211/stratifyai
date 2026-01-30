"""Google Gemini provider implementation."""

import os
from typing import Optional

from ..config import GOOGLE_MODELS, PROVIDER_BASE_URLS
from ..exceptions import AuthenticationError
from .openai_compatible import OpenAICompatibleProvider


class GoogleProvider(OpenAICompatibleProvider):
    """Google Gemini provider using OpenAI-compatible API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: dict = None
    ):
        """
        Initialize Google Gemini provider.
        
        Args:
            api_key: Google API key (defaults to GOOGLE_API_KEY env var)
            config: Optional provider-specific configuration
            
        Raises:
            AuthenticationError: If API key not provided
        """
        api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise AuthenticationError("google")
        
        base_url = PROVIDER_BASE_URLS["google"]
        super().__init__(api_key, base_url, GOOGLE_MODELS, config)
    
    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "google"
