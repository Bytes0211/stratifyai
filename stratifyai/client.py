"""Unified client for accessing multiple LLM providers."""

import asyncio
import logging
import time
from enum import Enum
from typing import AsyncIterator, Dict, Optional, Type, Union

logger = logging.getLogger(__name__)

from .config import MODEL_CATALOG
from .exceptions import (
    AuthenticationError,
    InvalidModelError,
    InvalidProviderError,
    MaxRetriesExceededError,
    ValidationError,
)
from .models import ChatRequest, ChatResponse, Message
from .retry import RetryConfig, exponential_backoff, with_retry
from .utils.reasoning_detector import is_reasoning_model
from .providers.base import BaseProvider
from .providers.openai import OpenAIProvider
from .providers.anthropic import AnthropicProvider
from .providers.google import GoogleProvider
from .providers.deepseek import DeepSeekProvider
from .providers.groq import GroqProvider
from .providers.grok import GrokProvider
from .providers.openrouter import OpenRouterProvider
from .providers.ollama import OllamaProvider
from .providers.bedrock import BedrockProvider
from .utils.sync_helpers import run_sync
from .api_key_helper import APIKeyHelper


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
_provider_pool: Dict[str, BaseProvider] = {}


def _pool_key(provider: str, api_key: Optional[str]) -> str:
    """Build a deterministic key for the provider pool."""
    # Use a short hash of the api_key so different keys get different clients
    key_part = str(hash(api_key))[:12] if api_key else "env"
    return f"{provider}:{key_part}"


def close_all_providers() -> None:
    """Release all pooled provider instances.

    Call this during application shutdown to clean up SDK clients.
    """
    _provider_pool.clear()
    logger.debug("All pooled provider instances released")


class LLMClient:
    """Unified client for all LLM providers."""

    # Provider registry maps provider names to provider classes
    _provider_registry: Dict[str, Type[BaseProvider]] = {
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
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        config: dict = None,
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
        self._provider_instance = None
        self._providers: Dict[str, BaseProvider] = {}
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
            raise AuthenticationError(provider, error_message)

    def _build_provider_config(self, provider: str) -> dict:
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
        self, cancel_event: Optional[asyncio.Event], model: Optional[str] = None
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
        if key in _provider_pool:
            provider_instance = _provider_pool[key]
        else:
            provider_class = self._provider_registry[provider]
            provider_instance = provider_class(
                api_key=self.api_key,
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
                return provider_name

        raise InvalidModelError(model, "any provider")

    async def chat(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        cancel_event: Optional[asyncio.Event] = None,
        **kwargs,
    ) -> Union[ChatResponse, AsyncIterator[ChatResponse]]:
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
            response = await _chat_call()
            response.latency_ms = (time.perf_counter() - start_time) * 1000
            return response

    async def chat_completion(
        self,
        request: ChatRequest,
        cancel_event: Optional[asyncio.Event] = None,
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
        response = await _completion_call()
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Add latency to response
        response.latency_ms = latency_ms
        return response

    async def chat_completion_stream(
        self,
        request: ChatRequest,
        cancel_event: Optional[asyncio.Event] = None,
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
        async for chunk in self._stream_with_retry(
            provider,
            request,
            cancel_event=cancel_event,
        ):
            yield chunk

    async def _stream_with_retry(
        self,
        provider: BaseProvider,
        request: ChatRequest,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> AsyncIterator[ChatResponse]:
        """Execute streaming requests with retry and cancellation support.

        Only retries on setup failures before any chunks are yielded.
        Once streaming has begun, exceptions are raised to prevent duplicate chunks.
        """
        cfg = self._retry_config
        chunks_yielded = 0

        for attempt in range(cfg.max_retries + 1):
            try:
                await self._check_cancellation(cancel_event, model=request.model)
                async for chunk in provider.chat_completion_stream(request):
                    await self._check_cancellation(cancel_event, model=request.model)
                    chunks_yielded += 1
                    yield chunk
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

    def chat_sync(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
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
        return run_sync(
            self.chat(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
                **kwargs,
            )
        )

    def chat_completion_sync(self, request: ChatRequest) -> ChatResponse:
        """
        Synchronous wrapper for chat_completion().

        Args:
            request: Unified chat request

        Returns:
            Chat completion response
        """
        return run_sync(self.chat_completion(request))

    def close(self) -> None:
        """Release this client's provider from the shared pool."""
        for prov_name, prov_inst in list(self._providers.items()):
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
    def get_supported_models(cls, provider: Optional[str] = None) -> list[str]:
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
        all_models = []
        for models in MODEL_CATALOG.values():
            all_models.extend(models.keys())
        return all_models
