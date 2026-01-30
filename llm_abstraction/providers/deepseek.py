"""DeepSeek provider implementation."""

import os
from typing import Optional

from ..config import DEEPSEEK_MODELS, PROVIDER_BASE_URLS
from ..exceptions import AuthenticationError
from .openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek provider using OpenAI-compatible API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: dict = None
    ):
        """
        Initialize DeepSeek provider.
        
        Args:
            api_key: DeepSeek API key (defaults to DEEPSEEK_API_KEY env var)
            config: Optional provider-specific configuration
            
        Raises:
            AuthenticationError: If API key not provided
        """
        api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise AuthenticationError("deepseek")
        
        base_url = PROVIDER_BASE_URLS["deepseek"]
        super().__init__(api_key, base_url, DEEPSEEK_MODELS, config)
    
    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "deepseek"
