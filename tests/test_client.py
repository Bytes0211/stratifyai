"""Unit tests for unified LLM client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.client import LLMClient
from stratifyai.exceptions import InvalidModelError, InvalidProviderError
from stratifyai.models import ChatRequest, Message


class TestLLMClient:
    """Tests for unified LLM client."""
    
    def test_client_initialization_without_provider(self):
        """Test client initialization without specifying provider."""
        client = LLMClient()
        assert client.provider_name is None
        assert client._provider_instance is None
    
    @patch('stratifyai.providers.openai.AsyncOpenAI')
    def test_client_initialization_with_provider(self, mock_openai):
        """Test client initialization with specific provider."""
        mock_openai.return_value = MagicMock()
        client = LLMClient(provider="openai", api_key="test-key")
        assert client.provider_name == "openai"
        assert client._provider_instance is not None
    
    def test_client_initialization_invalid_provider(self):
        """Test client initialization with invalid provider raises error."""
        with pytest.raises(InvalidProviderError):
            LLMClient(provider="invalid-provider")
    
    def test_detect_provider_openai(self):
        """Test provider detection for OpenAI models."""
        client = LLMClient()
        provider = client._detect_provider("gpt-4.1-mini")
        assert provider == "openai"
    
    def test_detect_provider_anthropic(self):
        """Test provider detection for Anthropic models."""
        client = LLMClient()
        provider = client._detect_provider("claude-3-5-sonnet-20241022")
        assert provider == "anthropic"
    
    def test_detect_provider_google(self):
        """Test provider detection for Google models."""
        client = LLMClient()
        provider = client._detect_provider("gemini-2.5-pro")
        assert provider == "google"
    
    def test_detect_provider_invalid_model(self):
        """Test provider detection with invalid model raises error."""
        client = LLMClient()
        with pytest.raises(InvalidModelError):
            client._detect_provider("nonexistent-model")
    
    @patch('stratifyai.providers.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_with_auto_detection(self, mock_openai):
        """Test chat method with automatic provider detection."""
        # Setup mock OpenAI client
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "id": "test",
            "model": "gpt-4.1-mini",
            "created": 1234567890,
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        }
        # Make create() return a coroutine
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Execute
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        response = await client.chat(model="gpt-4.1-mini", messages=messages)
        
        # Verify provider was initialized and called
        assert client._provider_instance is not None
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('stratifyai.providers.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_completion_request(self, mock_openai):
        """Test chat_completion method with ChatRequest."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "id": "test",
            "model": "gpt-4.1-mini",
            "created": 1234567890,
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        }
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Execute
        client = LLMClient(api_key="test-key")
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")]
        )
        response = await client.chat_completion(request)
        
        # Verify
        assert response.content == "Hi"
    
    @patch('stratifyai.providers.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_chat_with_parameters(self, mock_openai):
        """Test chat method with additional parameters."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "id": "test",
            "model": "gpt-4.1-mini",
            "created": 1234567890,
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
        }
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Execute
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        response = await client.chat(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.5,
            max_tokens=100
        )
        
        # Verify parameters were passed
        call_args = mock_client.chat.completions.create.call_args[1]
        assert call_args["temperature"] == 0.5
        assert call_args["max_tokens"] == 100
    
    def test_get_supported_providers(self):
        """Test getting list of supported providers."""
        providers = LLMClient.get_supported_providers()
        assert isinstance(providers, list)
        assert "openai" in providers
    
    def test_get_supported_models_all(self):
        """Test getting all supported models."""
        models = LLMClient.get_supported_models()
        assert isinstance(models, list)
        assert len(models) > 0
        assert "gpt-4.1-mini" in models
        assert "claude-3-5-sonnet-20241022" in models
    
    def test_get_supported_models_by_provider(self):
        """Test getting models for specific provider."""
        openai_models = LLMClient.get_supported_models(provider="openai")
        assert isinstance(openai_models, list)
        assert "gpt-4.1-mini" in openai_models
        assert "claude-3-5-sonnet-20241022" not in openai_models
    
    @patch('stratifyai.providers.openai.AsyncOpenAI')
    @pytest.mark.asyncio
    async def test_streaming_request(self, mock_openai):
        """Test streaming chat completion."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Create mock streaming chunks
        mock_chunk1 = MagicMock()
        mock_chunk1.model_dump.return_value = {
            "id": "test",
            "model": "gpt-4.1-mini",
            "created": 1234567890,
            "choices": [{"delta": {"content": "Hi"}, "finish_reason": None}],
        }
        mock_chunk1.choices = [MagicMock(delta=MagicMock(content="Hi"))]
        
        mock_chunk2 = MagicMock()
        mock_chunk2.model_dump.return_value = {
            "id": "test",
            "model": "gpt-4.1-mini",
            "created": 1234567890,
            "choices": [{"delta": {"content": "!"}, "finish_reason": "stop"}],
        }
        mock_chunk2.choices = [MagicMock(delta=MagicMock(content="!"))]
        
        # Create async iterator for streaming
        async def async_iter_chunks():
            yield mock_chunk1
            yield mock_chunk2
        
        mock_client.chat.completions.create = AsyncMock(return_value=async_iter_chunks())
        
        # Execute
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        stream = await client.chat(
            model="gpt-4.1-mini",
            messages=messages,
            stream=True
        )
        
        # Verify streaming was called and consume stream
        chunks = [chunk async for chunk in stream]
        assert len(chunks) == 2
