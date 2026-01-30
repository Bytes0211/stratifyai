"""OpenAI provider implementation."""

import os
from datetime import datetime
from typing import Iterator, List, Optional

from openai import OpenAI

from ..config import OPENAI_MODELS
from ..exceptions import AuthenticationError, InvalidModelError, ProviderAPIError
from ..models import ChatRequest, ChatResponse, Usage
from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation with cost tracking."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: dict = None
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            config: Optional provider-specific configuration
            
        Raises:
            AuthenticationError: If API key not provided
        """
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AuthenticationError("openai")
        super().__init__(api_key, config)
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize OpenAI client."""
        try:
            self._client = OpenAI(api_key=self.api_key)
        except Exception as e:
            raise ProviderAPIError(
                f"Failed to initialize OpenAI client: {str(e)}",
                "openai"
            )
    
    @property
    def provider_name(self) -> str:
        """Return provider name."""
        return "openai"
    
    def get_supported_models(self) -> List[str]:
        """Return list of supported OpenAI models."""
        return list(OPENAI_MODELS.keys())
    
    def chat_completion(self, request: ChatRequest) -> ChatResponse:
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
        
        # Build OpenAI-specific request parameters
        openai_params = {
            "model": request.model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
        }
        
        # Add optional parameters
        if request.max_tokens:
            openai_params["max_tokens"] = request.max_tokens
        if request.stop:
            openai_params["stop"] = request.stop
        
        # Add reasoning_effort for o-series models
        if request.reasoning_effort and "o" in request.model:
            openai_params["reasoning_effort"] = request.reasoning_effort
        
        # Add any extra params
        if request.extra_params:
            openai_params.update(request.extra_params)
        
        try:
            # Make API request
            raw_response = self._client.chat.completions.create(**openai_params)
            # Normalize and return
            return self._normalize_response(raw_response.model_dump())
        except Exception as e:
            raise ProviderAPIError(
                f"Chat completion failed: {str(e)}",
                self.provider_name
            )
    
    def chat_completion_stream(
        self, request: ChatRequest
    ) -> Iterator[ChatResponse]:
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
        
        # Build request parameters
        openai_params = {
            "model": request.model,
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in request.messages
            ],
            "stream": True,
            "temperature": request.temperature,
        }
        
        if request.max_tokens:
            openai_params["max_tokens"] = request.max_tokens
        
        try:
            stream = self._client.chat.completions.create(**openai_params)
            
            for chunk in stream:
                chunk_dict = chunk.model_dump()
                if chunk.choices and chunk.choices[0].delta.content:
                    yield self._normalize_stream_chunk(chunk_dict)
        except Exception as e:
            raise ProviderAPIError(
                f"Streaming chat completion failed: {str(e)}",
                self.provider_name
            )
    
    def _normalize_response(self, raw_response: dict) -> ChatResponse:
        """
        Convert OpenAI response to unified format.
        
        Args:
            raw_response: Raw OpenAI API response
            
        Returns:
            Normalized ChatResponse with cost
        """
        choice = raw_response["choices"][0]
        usage_dict = raw_response.get("usage", {})
        
        # Extract token usage
        usage = Usage(
            prompt_tokens=usage_dict.get("prompt_tokens", 0),
            completion_tokens=usage_dict.get("completion_tokens", 0),
            total_tokens=usage_dict.get("total_tokens", 0),
            cached_tokens=usage_dict.get("prompt_tokens_details", {}).get(
                "cached_tokens", 0
            ),
            reasoning_tokens=usage_dict.get("completion_tokens_details", {}).get(
                "reasoning_tokens", 0
            ),
        )
        
        # Calculate cost
        usage.cost_usd = self._calculate_cost(usage, raw_response["model"])
        
        return ChatResponse(
            id=raw_response["id"],
            model=raw_response["model"],
            content=choice["message"]["content"] or "",
            finish_reason=choice["finish_reason"],
            usage=usage,
            provider=self.provider_name,
            created_at=datetime.fromtimestamp(raw_response["created"]),
            raw_response=raw_response,
        )
    
    def _normalize_stream_chunk(self, chunk_dict: dict) -> ChatResponse:
        """Normalize streaming chunk to ChatResponse format."""
        choice = chunk_dict["choices"][0]
        content = choice["delta"].get("content", "")
        
        return ChatResponse(
            id=chunk_dict["id"],
            model=chunk_dict["model"],
            content=content,
            finish_reason=choice.get("finish_reason", ""),
            usage=Usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0
            ),
            provider=self.provider_name,
            created_at=datetime.fromtimestamp(chunk_dict["created"]),
            raw_response=chunk_dict,
        )
    
    def _calculate_cost(self, usage: Usage, model: str) -> float:
        """
        Calculate cost in USD based on token usage.
        
        Args:
            usage: Token usage information
            model: Model name used
            
        Returns:
            Cost in USD
        """
        model_info = OPENAI_MODELS.get(model, {})
        cost_input = model_info.get("cost_input", 0.0)
        cost_output = model_info.get("cost_output", 0.0)
        
        # Costs are per 1M tokens
        input_cost = (usage.prompt_tokens / 1_000_000) * cost_input
        output_cost = (usage.completion_tokens / 1_000_000) * cost_output
        
        return input_cost + output_cost
