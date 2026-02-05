"""Abstract base class for LLM providers."""

import asyncio
from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Optional

from ..models import ChatRequest, ChatResponse, Usage
from ..exceptions import ValidationError


class BaseProvider(ABC):
    """Abstract base class that all LLM providers must implement."""
    
    def __init__(self, api_key: str, config: dict = None):
        """
        Initialize provider with API key and optional configuration.
        
        Args:
            api_key: Provider API key
            config: Optional provider-specific configuration
        """
        self.api_key = api_key
        self.config = config or {}
        self._client = None
    
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
    async def chat_completion_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatResponse]:
        """
        Execute a streaming chat completion request.
        
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
        return asyncio.run(self.chat_completion(request))
    
    @abstractmethod
    def _normalize_response(self, raw_response: dict) -> ChatResponse:
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
    def get_supported_models(self) -> List[str]:
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
        self, 
        cache_creation_tokens: int,
        cache_read_tokens: int,
        model: str
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
    
    def validate_temperature(self, temperature: float, min_temp: float = 0.0, max_temp: float = 2.0) -> None:
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
