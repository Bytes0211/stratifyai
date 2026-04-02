"""Google Gemini provider implementation."""

from ..api_key_helper import get_api_key_or_error
from ..config import GOOGLE_MODELS, PROVIDER_BASE_URLS
from .openai_compatible import OpenAICompatibleProvider


class GoogleProvider(OpenAICompatibleProvider):
    """Google Gemini provider using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
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
        api_key = get_api_key_or_error("google", api_key)
        base_url = PROVIDER_BASE_URLS["google"]
        super().__init__(api_key, base_url, GOOGLE_MODELS, config)

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "google"
