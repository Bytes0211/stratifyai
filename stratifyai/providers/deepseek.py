"""DeepSeek provider implementation."""

from ..api_key_helper import get_api_key_or_error
from ..config import DEEPSEEK_MODELS, PROVIDER_BASE_URLS
from .openai_compatible import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek provider using OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        config: dict[str, object] | None = None,
    ):
        """
        Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key (defaults to DEEPSEEK_API_KEY env var)
            config: Optional provider-specific configuration

        Raises:
            AuthenticationError: If API key not provided
        """
        api_key = get_api_key_or_error("deepseek", api_key)
        base_url = PROVIDER_BASE_URLS["deepseek"]
        super().__init__(api_key, base_url, DEEPSEEK_MODELS, config)

    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "deepseek"
