"""OpenRouter provider implementation."""

from ..api_key_helper import get_api_key_or_error
from ..config import OPENROUTER_MODELS, PROVIDER_BASE_URLS
from .openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    """OpenRouter provider using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        config: dict[str, object] | None = None,
    ):
        """
        Initialize OpenRouter provider.

        Args:
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            config: Optional provider-specific configuration

        Raises:
            AuthenticationError: If API key not provided
        """
        api_key = get_api_key_or_error("openrouter", api_key)
        base_url = PROVIDER_BASE_URLS["openrouter"]
        super().__init__(api_key, base_url, OPENROUTER_MODELS, config)

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "openrouter"
