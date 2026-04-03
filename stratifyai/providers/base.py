"""Abstract base class for LLM providers."""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, cast

from ..config import PROVIDER_TIMEOUTS
from ..exceptions import ValidationError
from ..models import ChatRequest, ChatResponse, Usage
from ..utils.sync_helpers import run_sync


class BaseProvider(ABC):
    """Abstract base class that all LLM providers must implement."""

    def __init__(self, api_key: str, config: dict[str, Any] | None = None):
        """
        Initialize provider with API key and optional configuration.

        Args:
            api_key: Provider API key
            config: Optional provider-specific configuration
        """
        self.api_key = api_key
        self.config = config or {}
        self._client: Any = None
        provider_default_timeout = PROVIDER_TIMEOUTS.get(self.provider_name, 60.0)
        self.timeout_seconds = float(
            self.config.get("timeout_seconds", provider_default_timeout)
        )
        self.connect_timeout_seconds = float(
            self.config.get(
                "connect_timeout_seconds",
                min(10.0, self.timeout_seconds),
            )
        )
        # Concurrency limiter: limits simultaneous requests to this provider
        # Default: no limit (None). Set via set_concurrency_limit()
        self._concurrency_semaphore: asyncio.Semaphore | None = None
        self._concurrency_limit: int | None = None

    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize the provider-specific client library."""
        pass

    @abstractmethod
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """
        Execute a chat completion request.

        Args:
            request: Unified chat request

        Returns:
            Unified chat response

        Raises:
            InvalidModelError: If model not supported
            ProviderAPIError: If API call fails
        """
        pass

    @abstractmethod
    def chat_completion_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatResponse]:
        """
        Execute a streaming chat completion request.

        The returned async iterator **must** be fully consumed or explicitly
        closed via ``aclose()``.  When concurrency limits are enabled, the
        provider holds a semaphore slot for the lifetime of the generator;
        abandoning it without closing will leak the slot until GC finalises
        the object.  Using ``async for`` handles this automatically.

        Args:
            request: Unified chat request with stream=True

        Yields:
            Unified chat response chunks

        Raises:
            InvalidModelError: If model not supported
            ProviderAPIError: If API call fails
        """
        pass

    def chat_completion_sync(self, request: ChatRequest) -> ChatResponse:
        """
        Synchronous wrapper for chat_completion.

        Args:
            request: Unified chat request

        Returns:
            Unified chat response
        """
        return cast(ChatResponse, run_sync(self.chat_completion(request)))

    @abstractmethod
    def _normalize_response(
        self,
        raw_response: dict[str, Any],
        model: str | None = None,
    ) -> ChatResponse:
        """
        Convert provider-specific response to unified format.

        Args:
            raw_response: Raw response from provider API

        Returns:
            Normalized ChatResponse
        """
        pass

    @abstractmethod
    def _calculate_cost(self, usage: Usage, model: str) -> float:
        """
        Calculate cost for the request based on token usage.

        Args:
            usage: Token usage information
            model: Model name used

        Returns:
            Cost in USD
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic')."""
        pass

    @abstractmethod
    def get_supported_models(self) -> list[str]:
        """
        Return list of models supported by this provider.

        Returns:
            List of model names
        """
        pass

    def validate_model(self, model: str) -> bool:
        """
        Check if model is supported by this provider.

        Args:
            model: Model name to validate

        Returns:
            True if supported, False otherwise
        """
        return model in self.get_supported_models()

    def supports_caching(self, model: str) -> bool:
        """
        Check if model supports prompt caching.

        Args:
            model: Model name to check

        Returns:
            True if model supports prompt caching, False otherwise
        """
        # To be implemented by providers that support caching
        return False

    def _calculate_cache_cost(
        self, cache_creation_tokens: int, cache_read_tokens: int, model: str
    ) -> float:
        """
        Calculate cost for cached tokens.

        Args:
            cache_creation_tokens: Number of tokens written to cache
            cache_read_tokens: Number of tokens read from cache
            model: Model name used

        Returns:
            Cost in USD for cache operations
        """
        # Base implementation returns 0, override in providers that support caching
        return 0.0

    def validate_temperature(
        self, temperature: float, min_temp: float = 0.0, max_temp: float = 2.0
    ) -> None:
        """
        Validate temperature parameter is within provider constraints.

        Args:
            temperature: Temperature value to validate
            min_temp: Minimum allowed temperature (provider-specific)
            max_temp: Maximum allowed temperature (provider-specific)

        Raises:
            ValidationError: If temperature is out of range
        """
        if not (min_temp <= temperature <= max_temp):
            raise ValidationError(
                f"{self.provider_name} temperature must be between {min_temp} and {max_temp}, "
                f"got {temperature}"
            )

    def set_concurrency_limit(self, max_concurrent: int | None) -> None:
        """
        Set maximum concurrent requests for this provider.

        Args:
            max_concurrent: Maximum number of concurrent requests allowed.
                          None disables the limit (default behavior).
        """
        self._concurrency_limit = max_concurrent
        # Reset semaphore so it gets lazily recreated in the correct event loop.
        # In-flight requests that already acquired the old semaphore hold their
        # own reference and will release it correctly via _release_concurrency_slot.
        self._concurrency_semaphore = None

    async def _acquire_concurrency_slot(self) -> asyncio.Semaphore | None:
        """Acquire a concurrency slot, blocking if limit is reached.

        The semaphore is created lazily on first use so it binds to the
        running event loop rather than the loop (or lack thereof) that was
        active when ``set_concurrency_limit`` was called.

        Returns:
            The semaphore that was acquired, or None if no limit is set.
            Callers must pass this to ``_release_concurrency_slot`` so that
            the release targets the same semaphore even if the limit is
            changed mid-flight.
        """
        if self._concurrency_limit is not None:
            if self._concurrency_semaphore is None:
                self._concurrency_semaphore = asyncio.Semaphore(self._concurrency_limit)
            sem = self._concurrency_semaphore
            await sem.acquire()
            return sem
        return None

    def _release_concurrency_slot(self, sem: asyncio.Semaphore | None) -> None:
        """Release a concurrency slot.

        Args:
            sem: The semaphore returned by ``_acquire_concurrency_slot``.
        """
        if sem is not None:
            sem.release()

    def get_concurrency_limit(self) -> int | None:
        """Get the current concurrency limit for this provider."""
        return self._concurrency_limit
