"""Groq provider implementation."""

from ..api_key_helper import get_api_key_or_error
from ..config import GROQ_MODELS, PROVIDER_BASE_URLS
from .openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    """Groq provider using OpenAI-compatible API."""

    def __init__(self, api_key: str | None = None, config: dict = None):
        """
        Initialize Groq provider.

        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            config: Optional provider-specific configuration

        Raises:
            AuthenticationError: If API key not provided
        """
        api_key = get_api_key_or_error("groq", api_key)
        base_url = PROVIDER_BASE_URLS["groq"]
        super().__init__(api_key, base_url, GROQ_MODELS, config)

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "groq"
