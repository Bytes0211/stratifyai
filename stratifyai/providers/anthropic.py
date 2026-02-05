"""Anthropic provider implementation."""

import os
from datetime import datetime
from typing import AsyncIterator, List, Optional

from anthropic import AsyncAnthropic

from ..config import ANTHROPIC_MODELS, PROVIDER_CONSTRAINTS
from ..exceptions import AuthenticationError, InvalidModelError, ProviderAPIError
from ..models import ChatRequest, ChatResponse, Usage
from .base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic provider implementation with Messages API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: dict = None
    ):
        """
        Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            config: Optional provider-specific configuration
            
        Raises:
            AuthenticationError: If API key not provided
        """
        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise AuthenticationError("anthropic")
        super().__init__(api_key, config)
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Anthropic async client."""
        try:
            self._client = AsyncAnthropic(api_key=self.api_key)
        except Exception as e:
            raise ProviderAPIError(
                f"Failed to initialize Anthropic client: {str(e)}",
                "anthropic"
            )
    
    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "anthropic"
    
    def get_supported_models(self) -> List[str]:
        """Return list of supported Anthropic models."""
        return list(ANTHROPIC_MODELS.keys())
    
    def supports_caching(self, model: str) -> bool:
        """Check if model supports prompt caching."""
        model_info = ANTHROPIC_MODELS.get(model, {})
        return model_info.get("supports_caching", False)
    
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """
        Execute chat completion request using Messages API.
        
        Args:
            request: Unified chat request
            
        Returns:
            Unified chat response with cost tracking
            
        Raises:
            InvalidModelError: If model not supported
            ProviderAPIError: If API call fails
        """
        if not self.validate_model(request.model):
            raise InvalidModelError(request.model, self.provider_name)
        
        # Validate temperature constraints for Anthropic (0.0 to 1.0)
        constraints = PROVIDER_CONSTRAINTS.get(self.provider_name, {})
        self.validate_temperature(
            request.temperature,
            constraints.get("min_temperature", 0.0),
            constraints.get("max_temperature", 1.0)
        )
        
        # Convert messages to Anthropic format
        # Anthropic requires system message separate from messages array
        system_message = None
        messages = []
        
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                message_dict = {"role": msg.role, "content": msg.content}
                # Add cache_control if present and model supports caching
                if msg.cache_control and self.supports_caching(request.model):
                    message_dict["cache_control"] = msg.cache_control
                messages.append(message_dict)
        
        # Build Anthropic-specific request parameters
        anthropic_params = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 4096,  # Anthropic requires max_tokens
        }
        
        # Anthropic only allows one of temperature or top_p
        # Prefer temperature if it's not the default, otherwise use top_p if it's not default
        # Default temperature is 0.7, default top_p is 1.0
        if request.temperature != 0.7:
            # Temperature was explicitly set, use it
            anthropic_params["temperature"] = request.temperature
        elif request.top_p != 1.0:
            # top_p was explicitly set (not default), use it
            anthropic_params["top_p"] = request.top_p
        else:
            # Both are defaults, use temperature
            anthropic_params["temperature"] = request.temperature
        
        # Add system message if present
        if system_message:
            anthropic_params["system"] = system_message
        
        # Add optional parameters
        if request.stop:
            anthropic_params["stop_sequences"] = request.stop
        
        # Add any extra params
        if request.extra_params:
            anthropic_params.update(request.extra_params)
        
        try:
            # Make API request
            raw_response = await self._client.messages.create(**anthropic_params)
            # Normalize and return
            return self._normalize_response(raw_response.model_dump())
        except Exception as e:
            raise ProviderAPIError(
                f"Chat completion failed: {str(e)}",
                self.provider_name
            )
    
    async def chat_completion_stream(
        self, request: ChatRequest
    ) -> AsyncIterator[ChatResponse]:
        """
        Execute streaming chat completion request.
        
        Args:
            request: Unified chat request
            
        Yields:
            Unified chat response chunks
            
        Raises:
            InvalidModelError: If model not supported
            ProviderAPIError: If API call fails
        """
        if not self.validate_model(request.model):
            raise InvalidModelError(request.model, self.provider_name)
        
        # Validate temperature constraints for Anthropic (0.0 to 1.0)
        constraints = PROVIDER_CONSTRAINTS.get(self.provider_name, {})
        self.validate_temperature(
            request.temperature,
            constraints.get("min_temperature", 0.0),
            constraints.get("max_temperature", 1.0)
        )
        
        # Convert messages to Anthropic format
        system_message = None
        messages = []
        
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                messages.append({"role": msg.role, "content": msg.content})
        
        # Build request parameters
        anthropic_params = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens or 4096,
        }
        
        if system_message:
            anthropic_params["system"] = system_message
        
        try:
            async with self._client.messages.stream(**anthropic_params) as stream:
                async for chunk in stream.text_stream:
                    yield self._normalize_stream_chunk(chunk)
        except Exception as e:
            raise ProviderAPIError(
                f"Streaming chat completion failed: {str(e)}",
                self.provider_name
            )
    
    def _normalize_response(self, raw_response: dict) -> ChatResponse:
        """
        Convert Anthropic response to unified format.
        
        Args:
            raw_response: Raw Anthropic API response
            
        Returns:
            Normalized ChatResponse with cost
        """
        # Extract content from response
        content = ""
        if raw_response.get("content"):
            for block in raw_response["content"]:
                if block.get("type") == "text":
                    content += block.get("text", "")
        
        # Extract token usage
        usage_dict = raw_response.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_dict.get("input_tokens", 0),
            completion_tokens=usage_dict.get("output_tokens", 0),
            total_tokens=usage_dict.get("input_tokens", 0) + usage_dict.get("output_tokens", 0),
            cache_creation_tokens=usage_dict.get("cache_creation_input_tokens", 0),
            cache_read_tokens=usage_dict.get("cache_read_input_tokens", 0),
        )
        
        # Calculate cost including cache costs
        base_cost = self._calculate_cost(usage, raw_response["model"])
        cache_cost = self._calculate_cache_cost(
            usage.cache_creation_tokens,
            usage.cache_read_tokens,
            raw_response["model"]
        )
        usage.cost_usd = base_cost + cache_cost
        
        # Add cost breakdown
        if usage.cache_creation_tokens > 0 or usage.cache_read_tokens > 0:
            usage.cost_breakdown = {
                "base_cost": base_cost,
                "cache_cost": cache_cost,
                "total_cost": usage.cost_usd,
            }
        
        return ChatResponse(
            id=raw_response["id"],
            model=raw_response["model"],
            content=content,
            finish_reason=raw_response.get("stop_reason", "stop"),
            usage=usage,
            provider=self.provider_name,
            created_at=datetime.now(),  # Anthropic doesn't provide timestamp
            raw_response=raw_response,
        )
    
    def _normalize_stream_chunk(self, chunk: str) -> ChatResponse:
        """Normalize streaming chunk to ChatResponse format."""
        return ChatResponse(
            id="",
            model="",
            content=chunk,
            finish_reason="",
            usage=Usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            ),
            provider=self.provider_name,
            created_at=datetime.now(),
            raw_response={},
        )
    
    def _calculate_cost(self, usage: Usage, model: str) -> float:
        """
        Calculate cost in USD based on token usage (excluding cache costs).
        
        Args:
            usage: Token usage information
            model: Model name used
            
        Returns:
            Cost in USD
        """
        model_info = ANTHROPIC_MODELS.get(model, {})
        cost_input = model_info.get("cost_input", 0.0)
        cost_output = model_info.get("cost_output", 0.0)
        
        # Calculate non-cached prompt tokens
        non_cached_prompt_tokens = usage.prompt_tokens - usage.cache_read_tokens
        
        # Costs are per 1M tokens
        input_cost = (non_cached_prompt_tokens / 1_000_000) * cost_input
        output_cost = (usage.completion_tokens / 1_000_000) * cost_output
        
        return input_cost + output_cost
    
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
        model_info = ANTHROPIC_MODELS.get(model, {})
        
        # Check if model supports caching
        if not model_info.get("supports_caching", False):
            return 0.0
        
        cost_cache_write = model_info.get("cost_cache_write", 0.0)
        cost_cache_read = model_info.get("cost_cache_read", 0.0)
        
        # Costs are per 1M tokens
        write_cost = (cache_creation_tokens / 1_000_000) * cost_cache_write
        read_cost = (cache_read_tokens / 1_000_000) * cost_cache_read
        
        return write_cost + read_cost
