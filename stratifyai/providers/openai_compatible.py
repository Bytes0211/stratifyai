"""Base class for OpenAI-compatible providers."""

from datetime import datetime
from typing import AsyncIterator, Dict, List

from openai import AsyncOpenAI, APIStatusError, APIError

from ..config import PROVIDER_CONSTRAINTS
from ..exceptions import ProviderAPIError, InvalidModelError, InsufficientBalanceError, AuthenticationError
from ..models import ChatRequest, ChatResponse, Usage
from .base import BaseProvider


class OpenAICompatibleProvider(BaseProvider):
    """
    Base class for providers with OpenAI-compatible APIs.
    
    This includes: Google Gemini, DeepSeek, Groq, Grok, OpenRouter, Ollama.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model_catalog: Dict,
        config: dict = None
    ):
        """
        Initialize OpenAI-compatible provider.
        
        Args:
            api_key: Provider API key
            base_url: Provider base URL
            model_catalog: Model catalog for this provider
            config: Optional provider-specific configuration
        """
        super().__init__(api_key, config)
        self.base_url = base_url
        self.model_catalog = model_catalog
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize OpenAI-compatible async client."""
        try:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        except Exception as e:
            raise ProviderAPIError(
                f"Failed to initialize {self.provider_name} client: {str(e)}",
                self.provider_name
            )
    
    def get_supported_models(self) -> List[str]:
        """Return list of supported models."""
        return list(self.model_catalog.keys())
    
    def supports_caching(self, model: str) -> bool:
        """Check if model supports prompt caching."""
        model_info = self.model_catalog.get(model, {})
        return model_info.get("supports_caching", False)
    
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """
        Execute chat completion request.
        
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
        
        # Validate temperature constraints (most OpenAI-compatible providers use 0.0 to 2.0)
        constraints = PROVIDER_CONSTRAINTS.get(self.provider_name, {})
        self.validate_temperature(
            request.temperature,
            constraints.get("min_temperature", 0.0),
            constraints.get("max_temperature", 2.0)
        )
        
        # Build OpenAI-compatible request parameters
        messages = []
        for msg in request.messages:
            message_dict = {"role": msg.role, "content": msg.content}
            # Add cache_control if present and model supports caching
            if msg.cache_control and self.supports_caching(request.model):
                message_dict["cache_control"] = msg.cache_control
            messages.append(message_dict)
        
        openai_params = {
            "model": request.model,
            "messages": messages,
        }
        
        # Check if model is a reasoning model
        model_info = self.model_catalog.get(request.model, {})
        is_reasoning_model = model_info.get("reasoning_model", False)
        
        # Also check model name patterns for reasoning models
        if not is_reasoning_model and request.model:
            model_lower = request.model.lower()
            is_reasoning_model = (
                model_lower.startswith("o1") or 
                model_lower.startswith("o3") or
                model_lower.startswith("gpt-5") or
                "reasoner" in model_lower or
                "reasoning" in model_lower or
                (model_lower.startswith("o") and len(model_lower) > 1 and model_lower[1].isdigit())
            )
        
        # Only add temperature and sampling params for non-reasoning models
        if not is_reasoning_model:
            openai_params["temperature"] = request.temperature
            openai_params["top_p"] = request.top_p
            if request.frequency_penalty:
                openai_params["frequency_penalty"] = request.frequency_penalty
            if request.presence_penalty:
                openai_params["presence_penalty"] = request.presence_penalty
        
        # Add optional parameters
        if request.max_tokens:
            openai_params["max_tokens"] = request.max_tokens
        if request.stop:
            openai_params["stop"] = request.stop
        
        # Add any extra params
        if request.extra_params:
            openai_params.update(request.extra_params)
        
        try:
            # Make API request
            raw_response = await self._client.chat.completions.create(**openai_params)
            # Normalize and return
            return self._normalize_response(raw_response.model_dump())
        except (APIStatusError, APIError) as e:
            error_msg = str(e)
            # Check for specific error types
            if "insufficient balance" in error_msg.lower():
                raise InsufficientBalanceError(self.provider_name)
            elif "invalid_api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or (hasattr(e, 'status_code') and e.status_code == 401):
                raise AuthenticationError(self.provider_name)
            else:
                raise ProviderAPIError(
                    f"Chat completion failed: {error_msg}",
                    self.provider_name
                )
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
        
        # Validate temperature constraints (most OpenAI-compatible providers use 0.0 to 2.0)
        constraints = PROVIDER_CONSTRAINTS.get(self.provider_name, {})
        self.validate_temperature(
            request.temperature,
            constraints.get("min_temperature", 0.0),
            constraints.get("max_temperature", 2.0)
        )
        
        # Build request parameters
        openai_params = {
            "model": request.model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ],
            "stream": True,
        }
        
        # Check if model is a reasoning model
        model_info = self.model_catalog.get(request.model, {})
        is_reasoning_model = model_info.get("reasoning_model", False)
        
        # Also check model name patterns for reasoning models
        if not is_reasoning_model and request.model:
            model_lower = request.model.lower()
            is_reasoning_model = (
                model_lower.startswith("o1") or 
                model_lower.startswith("o3") or
                model_lower.startswith("gpt-5") or
                "reasoner" in model_lower or
                "reasoning" in model_lower or
                (model_lower.startswith("o") and len(model_lower) > 1 and model_lower[1].isdigit())
            )
        
        # Only add temperature for non-reasoning models
        if not is_reasoning_model:
            openai_params["temperature"] = request.temperature
        
        if request.max_tokens:
            openai_params["max_tokens"] = request.max_tokens
        
        try:
            stream = await self._client.chat.completions.create(**openai_params)
            
            async for chunk in stream:
                chunk_dict = chunk.model_dump()
                if chunk.choices and chunk.choices[0].delta.content:
                    yield self._normalize_stream_chunk(chunk_dict)
        except (APIStatusError, APIError) as e:
            error_msg = str(e)
            # Check for specific error types
            if "insufficient balance" in error_msg.lower():
                raise InsufficientBalanceError(self.provider_name)
            elif "invalid_api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or (hasattr(e, 'status_code') and e.status_code == 401):
                raise AuthenticationError(self.provider_name)
            else:
                raise ProviderAPIError(
                    f"Streaming chat completion failed: {error_msg}",
                    self.provider_name
                )
        except Exception as e:
            raise ProviderAPIError(
                f"Streaming chat completion failed: {str(e)}",
                self.provider_name
            )
    
    def _normalize_response(self, raw_response: dict) -> ChatResponse:
        """
        Convert OpenAI-compatible response to unified format.
        
        Args:
            raw_response: Raw API response
            
        Returns:
            Normalized ChatResponse with cost
        """
        choice = raw_response["choices"][0]
        usage_dict = raw_response.get("usage") or {}
        
        # Extract token usage
        prompt_details = usage_dict.get("prompt_tokens_details") or {}
        usage = Usage(
            prompt_tokens=usage_dict.get("prompt_tokens", 0),
            completion_tokens=usage_dict.get("completion_tokens", 0),
            total_tokens=usage_dict.get("total_tokens", 0),
            cached_tokens=prompt_details.get("cached_tokens", 0),
            cache_creation_tokens=prompt_details.get("cache_creation_input_tokens", 0),
            cache_read_tokens=prompt_details.get("cached_tokens", 0),
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
            id=raw_response.get("id", ""),
            model=raw_response["model"],
            content=choice["message"]["content"] or "",
            finish_reason=choice["finish_reason"],
            usage=usage,
            provider=self.provider_name,
            created_at=datetime.fromtimestamp(raw_response.get("created", 0)) if raw_response.get("created") else datetime.now(),
            raw_response=raw_response,
        )
    
    def _normalize_stream_chunk(self, chunk_dict: dict) -> ChatResponse:
        """Normalize streaming chunk to ChatResponse format."""
        choice = chunk_dict["choices"][0]
        content = choice["delta"].get("content", "")
        
        return ChatResponse(
            id=chunk_dict.get("id", ""),
            model=chunk_dict["model"],
            content=content,
            finish_reason=choice.get("finish_reason", ""),
            usage=Usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            ),
            provider=self.provider_name,
            created_at=datetime.fromtimestamp(chunk_dict.get("created", 0)) if chunk_dict.get("created") else datetime.now(),
            raw_response=chunk_dict,
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
        model_info = self.model_catalog.get(model, {})
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
        model_info = self.model_catalog.get(model, {})
        
        # Check if model supports caching
        if not model_info.get("supports_caching", False):
            return 0.0
        
        cost_cache_write = model_info.get("cost_cache_write", 0.0)
        cost_cache_read = model_info.get("cost_cache_read", 0.0)
        
        # Costs are per 1M tokens
        write_cost = (cache_creation_tokens / 1_000_000) * cost_cache_write
        read_cost = (cache_read_tokens / 1_000_000) * cost_cache_read
        
        return write_cost + read_cost
