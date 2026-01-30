"""Abstract base class for LLM providers."""

from abc import ABC, abstractmethod
from typing import Iterator, List, Optional

from ..models import ChatRequest, ChatResponse, Usage


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
    def chat_completion(self, request: ChatRequest) -> ChatResponse:
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
    ) -> Iterator[ChatResponse]:
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
