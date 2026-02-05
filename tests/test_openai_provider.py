"""Unit tests for OpenAI provider."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.exceptions import (
    AuthenticationError,
    InvalidModelError,
    ProviderAPIError,
)
from stratifyai.models import ChatRequest, Message
from stratifyai.providers.openai import OpenAIProvider


class TestOpenAIProvider:
    """Tests for OpenAI provider."""
    
    def test_initialization_with_api_key(self):
        """Test provider initialization with explicit API key."""
        with patch('stratifyai.providers.openai.AsyncOpenAI'):
            provider = OpenAIProvider(api_key="test-key")
            assert provider.api_key == "test-key"
            assert provider.provider_name == "openai"
    
    def test_initialization_without_api_key(self):
        """Test provider initialization fails without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises((AuthenticationError, ValueError)):
                OpenAIProvider()
    
    def test_initialization_with_env_var(self):
        """Test provider initialization from environment variable."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-key'}):
            with patch('stratifyai.providers.openai.AsyncOpenAI'):
                provider = OpenAIProvider()
                assert provider.api_key == "env-key"
    
    def test_get_supported_models(self):
        """Test getting list of supported models."""
        with patch('stratifyai.providers.openai.AsyncOpenAI'):
            provider = OpenAIProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert "gpt-4.1-mini" in models
            assert "gpt-5" in models
            assert "o1" in models
    
    def test_validate_model(self):
        """Test model validation."""
        with patch('stratifyai.providers.openai.AsyncOpenAI'):
            provider = OpenAIProvider(api_key="test-key")
            assert provider.validate_model("gpt-4.1-mini") is True
            assert provider.validate_model("invalid-model") is False
    
    @pytest.mark.asyncio
    async def test_chat_completion_invalid_model(self):
        """Test chat completion with invalid model raises error."""
        with patch('stratifyai.providers.openai.AsyncOpenAI'):
            provider = OpenAIProvider(api_key="test-key")
            request = ChatRequest(
                model="invalid-model",
                messages=[Message(role="user", content="Hello")]
            )
            with pytest.raises(InvalidModelError):
                await provider.chat_completion(request)
    
    @patch('stratifyai.providers.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, mock_openai_class):
        """Test successful chat completion."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = {
            "id": "chatcmpl-123",
            "model": "gpt-4.1-mini",
            "created": int(datetime.now().timestamp()),
            "choices": [{
                "message": {"content": "Hello! How can I help?"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
                "prompt_tokens_details": {"cached_tokens": 0},
                "completion_tokens_details": {"reasoning_tokens": 0}
            }
        }
        
        mock_completion = MagicMock()
        mock_completion.model_dump.return_value = mock_response
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        
        # Execute
        provider = OpenAIProvider(api_key="test-key")
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")]
        )
        response = await provider.chat_completion(request)
        
        # Verify
        assert response.id == "chatcmpl-123"
        assert response.model == "gpt-4.1-mini"
        assert response.content == "Hello! How can I help?"
        assert response.finish_reason == "stop"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 20
        assert response.usage.total_tokens == 30
        assert response.provider == "openai"
    
    @patch('stratifyai.providers.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_cost_calculation(self, mock_openai_class):
        """Test cost calculation for requests."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        mock_response = {
            "id": "chatcmpl-123",
            "model": "gpt-4.1-mini",
            "created": int(datetime.now().timestamp()),
            "choices": [{
                "message": {"content": "Response"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 1000,  # 1000 tokens
                "completion_tokens": 2000,  # 2000 tokens
                "total_tokens": 3000,
                "prompt_tokens_details": {"cached_tokens": 0},
                "completion_tokens_details": {"reasoning_tokens": 0}
            }
        }
        
        mock_completion = MagicMock()
        mock_completion.model_dump.return_value = mock_response
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        
        provider = OpenAIProvider(api_key="test-key")
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Test")]
        )
        response = await provider.chat_completion(request)
        
        # gpt-4.1-mini: $0.15/1M input, $0.60/1M output
        # Expected: (1000/1M * 0.15) + (2000/1M * 0.60) = 0.00015 + 0.0012 = 0.00135
        expected_cost = (1000 / 1_000_000 * 0.15) + (2000 / 1_000_000 * 0.60)
        assert abs(response.usage.cost_usd - expected_cost) < 0.00001
    
    @patch('stratifyai.providers.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_completion_with_options(self, mock_openai_class):
        """Test chat completion with additional options."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        provider = OpenAIProvider(api_key="test-key")
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
            temperature=0.5,
            max_tokens=500,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.5,
            stop=["END"]
        )
        
        # Mock response to avoid error
        mock_completion = MagicMock()
        mock_completion.model_dump.return_value = {
            "id": "test",
            "model": "gpt-4.1-mini",
            "created": int(datetime.now().timestamp()),
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        }
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        
        await provider.chat_completion(request)
        
        # Verify parameters were passed correctly
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["temperature"] == 0.5
        assert call_args["max_tokens"] == 500
        assert call_args["top_p"] == 0.9
        assert call_args["frequency_penalty"] == 0.5
        assert call_args["presence_penalty"] == 0.5
        assert call_args["stop"] == ["END"]
