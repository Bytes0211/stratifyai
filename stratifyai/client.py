"""Unified client for accessing multiple LLM providers."""

import asyncio
import time
from enum import Enum
from typing import AsyncIterator, Dict, Optional, Type, Union

from .config import MODEL_CATALOG
from .exceptions import InvalidModelError, InvalidProviderError
from .models import ChatRequest, ChatResponse, Message
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
        config: dict = None
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
        
        # Initialize provider if specified
        if provider:
            self._initialize_provider(provider)
    
    def _initialize_provider(self, provider: str) -> None:
        """
        Initialize a specific provider.
        
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
        
        provider_class = self._provider_registry[provider]
        self._provider_instance = provider_class(
            api_key=self.api_key,
            config=self.config
        )
    
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
        
        raise InvalidModelError(
            model,
            "any provider"
        )
    
    async def chat(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
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
        # Auto-detect provider if not set
        if not self._provider_instance:
            provider = self._detect_provider(model)
            self._initialize_provider(provider)
        
        # Build request
        request = ChatRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs
        )
        
        # Execute request
        if stream:
            return self._provider_instance.chat_completion_stream(request)
        else:
            return await self._provider_instance.chat_completion(request)
    
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
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
        # Auto-detect provider if not set
        if not self._provider_instance:
            provider = self._detect_provider(request.model)
            self._initialize_provider(provider)
        
        # Capture timing
        start_time = time.perf_counter()
        response = await self._provider_instance.chat_completion(request)
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Add latency to response
        response.latency_ms = latency_ms
        return response
    
    async def chat_completion_stream(
        self, request: ChatRequest
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
        # Auto-detect provider if not set
        if not self._provider_instance:
            provider = self._detect_provider(request.model)
            self._initialize_provider(provider)
        
        return self._provider_instance.chat_completion_stream(request)
    
    def chat_sync(
        self,
        model: str,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
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
        return asyncio.run(self.chat(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
            **kwargs
        ))
    
    def chat_completion_sync(self, request: ChatRequest) -> ChatResponse:
        """
        Synchronous wrapper for chat_completion().
        
        Args:
            request: Unified chat request
            
        Returns:
            Chat completion response
        """
        return asyncio.run(self.chat_completion(request))
    
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
