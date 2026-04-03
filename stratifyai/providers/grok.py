"""Grok (X.AI) provider implementation."""

from ..api_key_helper import get_api_key_or_error
from ..config import GROK_MODELS, PROVIDER_BASE_URLS
from .openai_compatible import OpenAICompatibleProvider


class GrokProvider(OpenAICompatibleProvider):
    """Grok (X.AI) provider using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        config: dict[str, object] | None = None,
    ):
        """
        Initialize Grok provider.

        Args:
            api_key: Grok API key (defaults to XAI_API_KEY or GROK_API_KEY env var)
            config: Optional provider-specific configuration

        Raises:
            AuthenticationError: If API key not provided
        """
        # Support both XAI_API_KEY (official) and GROK_API_KEY (legacy)
        api_key = get_api_key_or_error("grok", api_key)

        base_url = PROVIDER_BASE_URLS["grok"]
        super().__init__(api_key, base_url, GROK_MODELS, config)

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "grok"
