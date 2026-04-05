"""Unified client for accessing multiple LLM providers."""

import asyncio
import hashlib
import logging
import threading
import time
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any, cast

from .api_key_helper import APIKeyHelper
from .config import MODEL_CATALOG
from .exceptions import (
    AuthenticationError,
    InvalidModelError,
    InvalidProviderError,
    MaxRetriesExceededError,
    ValidationError,
)
from .models import ChatRequest, ChatResponse, Message
from .providers.anthropic import AnthropicProvider
from .providers.base import BaseProvider
from .providers.bedrock import BedrockProvider
from .providers.deepseek import DeepSeekProvider
from .providers.google import GoogleProvider
from .providers.grok import GrokProvider
from .providers.groq import GroqProvider
from .providers.ollama import OllamaProvider
from .providers.openai import OpenAIProvider
from .providers.openrouter import OpenRouterProvider
from .retry import RetryConfig, exponential_backoff, with_retry
from .utils.reasoning_detector import is_reasoning_model
from .utils.sync_helpers import run_sync

logger = logging.getLogger(__name__)


class ProviderType(str, Enum):
    """Supported provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    GROQ = "groq"
    GROK = "grok"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    BEDROCK = "bedrock"


# Module-level provider pool shared across all LLMClient instances.
# Key: "<provider_name>:<api_key_hash>" → BaseProvider instance.
# Prevents creating duplicate SDK clients (AsyncOpenAI, AsyncAnthropic, …)
# when multiple LLMClient objects target the same provider.
_provider_pool: dict[str, BaseProvider] = {}
_provider_pool_lock = threading.Lock()


def _pool_key(provider: str, api_key: str | None) -> str:
    """Build a deterministic key for the provider pool.

    Uses SHA-256 (stable across processes) instead of Python's hash()
    which is randomized per process via PYTHONHASHSEED.
    """
    if api_key:
        key_part = hashlib.sha256(api_key.encode()).hexdigest()[:12]
    else:
        key_part = "env"
    return f"{provider}:{key_part}"


def close_all_providers() -> None:
    """Release all pooled provider instances.

    Call this during application shutdown to clean up SDK clients.
    """
    with _provider_pool_lock:
        _provider_pool.clear()
    logger.debug("All pooled provider instances released")


async def _safe_aclose_async_iterator(iterator: Any) -> None:
    """Explicitly close async generators/iterators when supported."""
    aclose = getattr(iterator, "aclose", None)
    if not callable(aclose):
        return

    result = aclose()
    if asyncio.iscoroutine(result):
        await result


class LLMClient:
    """Unified client for all LLM providers."""

    # Provider registry maps provider names to provider classes
    _provider_registry: dict[str, type[BaseProvider]] = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "deepseek": DeepSeekProvider,
        "groq": GroqProvider,
        "grok": GrokProvider,
        "openrouter": OpenRouterProvider,
        "ollama": OllamaProvider,
        "bedrock": BedrockProvider,
    }

    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        config: dict[str, Any] | None = None,
    ):
        """
        Initialize unified LLM client.

        Args:
            provider: Provider name (openai, anthropic, etc.)
                     If None, provider will be auto-detected from model name
            api_key: API key for the provider (defaults to env var)
            config: Optional provider-specific configuration

        Raises:
            InvalidProviderError: If provider is not supported
        """
        self.provider_name = provider
        self.api_key = api_key
        self.config = config or {}
        self._provider_instance: BaseProvider | None = None
        self._providers: dict[str, BaseProvider] = {}
        self._retry_config = self._build_retry_config()

        # Fail-fast API key validation when provider is explicit.
        if provider:
            self._validate_provider_auth(provider)

        # Initialize provider if specified
        if provider:
            self._initialize_provider(provider)

    def _build_retry_config(self) -> RetryConfig:
        """Build retry configuration from client config."""
        retry_cfg = self.config.get("retry", {})
        if not isinstance(retry_cfg, dict):
            retry_cfg = {}

        return RetryConfig(
            max_retries=int(retry_cfg.get("max_retries", 3)),
            initial_delay=float(retry_cfg.get("initial_delay", 1.0)),
            max_delay=float(retry_cfg.get("max_delay", 60.0)),
            exponential_base=float(retry_cfg.get("exponential_base", 2.0)),
            jitter=bool(retry_cfg.get("jitter", True)),
        )

    def _validate_provider_auth(self, provider: str) -> None:
        """Validate provider authentication settings at client init time."""
        if provider not in self._provider_registry:
            return

        # Providers that can rely on local/default credentials should not hard-fail.
        if provider in {"ollama", "bedrock"}:
            return

        is_valid, error_message = APIKeyHelper.validate_api_key(provider, self.api_key)
        if not is_valid:
            raise AuthenticationError(
                provider,
                error_message or f"Missing or invalid API key for {provider}.",
            )

    def _build_provider_config(self, provider: str) -> dict[str, Any]:
        """Build provider-specific config with optional per-provider overrides."""
        provider_config = dict(self.config)
        providers_cfg = provider_config.pop("providers", None)
        if isinstance(providers_cfg, dict):
            specific_cfg = providers_cfg.get(provider, {})
            if isinstance(specific_cfg, dict):
                provider_config.update(specific_cfg)
        return provider_config

    def _validate_reasoning_temperature(self, model: str, temperature: float) -> None:
        """Enforce client-level temperature requirements for reasoning models."""
        provider = self._detect_provider(model)
        if is_reasoning_model(provider, model, MODEL_CATALOG) and temperature != 1.0:
            raise ValidationError(
                f"Reasoning model '{model}' requires temperature=1.0, got {temperature}"
            )

    async def _check_cancellation(
        self, cancel_event: asyncio.Event | None, model: str | None = None
    ) -> None:
        """Raise cancellation when the provided cancel event is set."""
        if cancel_event and cancel_event.is_set():
            if model:
                logger.info("Request cancelled before completion for model=%s", model)
            raise asyncio.CancelledError()

    def _initialize_provider(self, provider: str) -> None:
        """
        Initialize a specific provider.

        Checks the module-level ``_provider_pool`` first so that multiple
        ``LLMClient`` instances targeting the same provider share one SDK
        client (and therefore one connection pool).

        Args:
            provider: Provider name

        Raises:
            InvalidProviderError: If provider not supported
        """
        if provider not in self._provider_registry:
            raise InvalidProviderError(
                f"Provider '{provider}' not supported. "
                f"Available providers: {list(self._provider_registry.keys())}"
            )

        key = _pool_key(provider, self.api_key)
        with _provider_pool_lock:
            provider_instance = _provider_pool.get(key)
            if provider_instance is None:
                provider_class = self._provider_registry[provider]
                provider_instance = provider_class(
                    api_key=self.api_key or "",
                    config=self._build_provider_config(provider),
                )
                _provider_pool[key] = provider_instance

        self._providers[provider] = provider_instance
        self._provider_instance = provider_instance
        self.provider_name = provider

    def _get_provider_for_model(self, model: str) -> BaseProvider:
        """
        Get provider instance for a model, auto-detecting and caching as needed.

        Args:
            model: Model name

        Returns:
            Initialized provider instance for the detected provider
        """
        detected_provider = self._detect_provider(model)
        if detected_provider not in self._providers:
            self._initialize_provider(detected_provider)

        provider = self._providers[detected_provider]
        self._provider_instance = provider
        self.provider_name = detected_provider
        return provider

    def _detect_provider(self, model: str) -> str:
        """
        Auto-detect provider from model name.

        Args:
            model: Model name

        Returns:
            Provider name

        Raises:
            InvalidModelError: If model not found in any provider
        """
        for provider_name, models in MODEL_CATALOG.items():
            if model in models:
                return str(provider_name)

        raise InvalidModelError(model, "any provider")

    def set_provider_concurrency_limit(
        self, provider: str, max_concurrent: int | None
    ) -> None:
        """
        Set maximum concurrent requests for a specific provider.

        Args:
            provider: Provider name (e.g., 'openai', 'anthropic')
            max_concurrent: Maximum number of concurrent requests.
                          None removes the limit (default behavior).

        Raises:
            InvalidProviderError: If provider is not supported
        """
        if provider not in self._provider_registry:
            raise InvalidProviderError(f"Provider '{provider}' is not supported")

        # Initialize provider if not already done
        if provider not in self._providers:
            self._initialize_provider(provider)

        # Set limit on the provider instance
        self._providers[provider].set_concurrency_limit(max_concurrent)
        logger.debug(
            "Set concurrency limit for %s: %s", provider, max_concurrent or "unlimited"
        )

    def get_provider_concurrency_limit(self, provider: str) -> int | None:
        """
        Get the current concurrency limit for a provider.

        Args:
            provider: Provider name

        Returns:
            Current limit, or None if no limit is set

        Raises:
            InvalidProviderError: If provider is not supported
        """
        if provider not in self._provider_registry:
            raise InvalidProviderError(f"Provider '{provider}' is not supported")

        if provider not in self._providers:
            # Provider not yet initialized, no limit set
            return None

        limit: int | None = self._providers[provider].get_concurrency_limit()
        return limit

    async def chat(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        stream: bool = False,
        cancel_event: asyncio.Event | None = None,
        **kwargs,
    ) -> ChatResponse | AsyncIterator[ChatResponse]:
        """
        Execute a chat completion request.

        Args:
            model: Model name (e.g., "gpt-4.1-mini", "claude-3-5-sonnet")
            messages: List of conversation messages
            temperature: Sampling temperature (0.0 - 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional provider-specific parameters

        Returns:
            Chat completion response, or AsyncIterator if streaming

        Raises:
            InvalidModelError: If model not supported
            InvalidProviderError: If provider not supported
        """
        await self._check_cancellation(cancel_event, model=model)
        self._validate_reasoning_temperature(model, temperature)

        provider = self._get_provider_for_model(model)

        # Build request
        request = ChatRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs,
        )

        # Execute request
        if stream:
            return self._stream_with_retry(provider, request, cancel_event=cancel_event)
        else:

            @with_retry(config=self._retry_config)
            async def _chat_call() -> ChatResponse:
                await self._check_cancellation(cancel_event, model=model)
                return await provider.chat_completion(request)

            start_time = time.perf_counter()
            response = cast(ChatResponse, await _chat_call())
            response.latency_ms = (time.perf_counter() - start_time) * 1000
            return response

    async def chat_with_mcp(
        self,
        model: str,
        messages: list[Message],
        mcp_engine: Any,
        active_servers: list[str] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Execute a chat completion with MCP tool-use support."""
        self._validate_reasoning_temperature(model, temperature)
        provider = self._detect_provider(model)

        return await mcp_engine.chat_with_mcp(
            llm_client=self,
            provider=provider,
            model=model,
            messages=messages,
            active_servers=active_servers,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )

    async def chat_completion(
        self,
        request: ChatRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> ChatResponse:
        """
        Execute a chat completion request using ChatRequest object.

        Args:
            request: Unified chat request

        Returns:
            Chat completion response

        Raises:
            InvalidModelError: If model not supported
            InvalidProviderError: If provider not supported
        """
        await self._check_cancellation(cancel_event, model=request.model)
        self._validate_reasoning_temperature(request.model, request.temperature)
        provider = self._get_provider_for_model(request.model)

        @with_retry(config=self._retry_config)
        async def _completion_call() -> ChatResponse:
            await self._check_cancellation(cancel_event, model=request.model)
            return await provider.chat_completion(request)

        # Capture timing
        start_time = time.perf_counter()
        response = cast(ChatResponse, await _completion_call())
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Add latency to response
        response.latency_ms = latency_ms
        return response

    async def chat_completion_stream(
        self,
        request: ChatRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[ChatResponse]:
        """
        Execute a streaming chat completion request.

        Args:
            request: Unified chat request

        Yields:
            Chat completion response chunks

        Raises:
            InvalidModelError: If model not supported
            InvalidProviderError: If provider not supported
        """
        await self._check_cancellation(cancel_event, model=request.model)
        self._validate_reasoning_temperature(request.model, request.temperature)
        provider = self._get_provider_for_model(request.model)
        stream = self._stream_with_retry(
            provider,
            request,
            cancel_event=cancel_event,
        )
        try:
            async for chunk in stream:
                yield chunk
        finally:
            await _safe_aclose_async_iterator(stream)

    async def _stream_with_retry(
        self,
        provider: BaseProvider,
        request: ChatRequest,
        cancel_event: asyncio.Event | None = None,
    ) -> AsyncIterator[ChatResponse]:
        """Execute streaming requests with retry and cancellation support.

        Only retries on setup failures before any chunks are yielded.
        Once streaming has begun, exceptions are raised to prevent duplicate chunks.
        """
        cfg = self._retry_config
        chunks_yielded = 0

        for attempt in range(cfg.max_retries + 1):
            stream = None
            try:
                await self._check_cancellation(cancel_event, model=request.model)
                stream = provider.chat_completion_stream(request)
                try:
                    async for chunk in stream:
                        await self._check_cancellation(
                            cancel_event, model=request.model
                        )
                        chunks_yielded += 1
                        yield chunk
                finally:
                    await _safe_aclose_async_iterator(stream)
                return
            except asyncio.CancelledError:
                raise
            except cfg.retry_on_exceptions as exc:
                if chunks_yielded > 0 or attempt == cfg.max_retries:
                    raise MaxRetriesExceededError(cfg.max_retries, exc) from exc

                delay = exponential_backoff(
                    attempt,
                    initial_delay=cfg.initial_delay,
                    exponential_base=cfg.exponential_base,
                    max_delay=cfg.max_delay,
                    jitter=cfg.jitter,
                )
                logger.warning(
                    "Streaming retry attempt %s/%s for model=%s after %.2fs: %s",
                    attempt + 1,
                    cfg.max_retries,
                    request.model,
                    delay,
                    str(exc),
                )
                await asyncio.sleep(delay)
            except Exception:
                # Non-retryable exceptions must propagate immediately
                raise

    def chat_sync(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs,
    ) -> ChatResponse:
        """
        Synchronous wrapper for chat().

        Args:
            model: Model name
            messages: List of conversation messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            Chat completion response
        """
        return cast(
            ChatResponse,
            run_sync(
                self.chat(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                    **kwargs,
                )
            ),
        )

    def chat_with_mcp_sync(
        self,
        model: str,
        messages: list[Message],
        mcp_engine: Any,
        active_servers: list[str] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> ChatResponse:
        """Synchronous wrapper for MCP-enabled chat."""
        return cast(
            ChatResponse,
            run_sync(
                self.chat_with_mcp(
                    model=model,
                    messages=messages,
                    mcp_engine=mcp_engine,
                    active_servers=active_servers,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
            ),
        )

    def chat_completion_sync(self, request: ChatRequest) -> ChatResponse:
        """
        Synchronous wrapper for chat_completion().

        Args:
            request: Unified chat request

        Returns:
            Chat completion response
        """
        return cast(ChatResponse, run_sync(self.chat_completion(request)))

    def close(self) -> None:
        """Release this client's provider from the shared pool."""
        with _provider_pool_lock:
            for prov_name, _prov_inst in list(self._providers.items()):
                key = _pool_key(prov_name, self.api_key)
                _provider_pool.pop(key, None)
        self._providers.clear()
        self._provider_instance = None

    async def __aenter__(self) -> "LLMClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @classmethod
    def get_supported_providers(cls) -> list[str]:
        """
        Get list of supported providers.

        Returns:
            List of provider names
        """
        return list(cls._provider_registry.keys())

    @classmethod
    def get_supported_models(cls, provider: str | None = None) -> list[str]:
        """
        Get list of supported models.

        Args:
            provider: Optional provider name to filter models

        Returns:
            List of model names
        """
        if provider:
            return list(MODEL_CATALOG.get(provider, {}).keys())

        # Return all models from all providers
        all_models: list[str] = []
        for models in MODEL_CATALOG.values():
            all_models.extend(models.keys())
        return all_models
