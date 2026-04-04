"""Unit tests for unified LLM client."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.client import LLMClient
from stratifyai.exceptions import (
    AuthenticationError,
    InvalidModelError,
    InvalidProviderError,
    ProviderAPIError,
    ValidationError,
)
from stratifyai.models import ChatRequest, ChatResponse, Message, Usage


class TestLLMClient:
    """Tests for unified LLM client."""

    def test_client_initialization_without_provider(self):
        """Test client initialization without specifying provider."""
        client = LLMClient()
        assert client.provider_name is None
        assert client._provider_instance is None
        assert client._providers == {}

    @patch("stratifyai.providers.openai.AsyncOpenAI")
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

    @patch("stratifyai.providers.openai.AsyncOpenAI")
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
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        # Make create() return a coroutine
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Execute
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        await client.chat(model="gpt-4.1-mini", messages=messages)

        # Verify provider was initialized and called
        assert client._provider_instance is not None
        mock_client.chat.completions.create.assert_called_once()

    @patch("stratifyai.providers.openai.AsyncOpenAI")
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
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Execute
        client = LLMClient(api_key="test-key")
        request = ChatRequest(
            model="gpt-4.1-mini", messages=[Message(role="user", content="Hello")]
        )
        response = await client.chat_completion(request)

        # Verify
        assert response.content == "Hi"
        assert response.latency_ms is not None
        assert response.latency_ms > 0

    @patch("stratifyai.providers.openai.AsyncOpenAI")
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
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Execute
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        await client.chat(
            model="gpt-4.1-mini", messages=messages, temperature=0.5, max_tokens=100
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

    @patch("stratifyai.providers.openai.AsyncOpenAI")
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

        mock_client.chat.completions.create = AsyncMock(
            return_value=async_iter_chunks()
        )

        # Execute
        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        stream = await client.chat(model="gpt-4.1-mini", messages=messages, stream=True)

        # Verify streaming was called and consume stream
        chunks = [chunk async for chunk in stream]
        assert len(chunks) == 2

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_chat_non_streaming_populates_latency(self, mock_openai):
        """Test chat() non-streaming path populates latency_ms."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        mock_response = MagicMock()
        mock_response.model_dump.return_value = {
            "id": "test",
            "model": "gpt-4.1-mini",
            "created": 1234567890,
            "choices": [{"message": {"content": "Hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]
        response = await client.chat(model="gpt-4.1-mini", messages=messages)

        assert response.latency_ms is not None
        assert response.latency_ms > 0

    @pytest.mark.asyncio
    async def test_chat_with_mcp_delegates_to_engine(self):
        """Test MCP-enabled chat delegates through the client-engine loop."""
        client = LLMClient()
        response = ChatResponse(
            id="mcp-1",
            model="gpt-4.1-mini",
            content="Done with MCP help",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
        )

        engine = MagicMock()
        engine.chat_with_mcp = AsyncMock(return_value=response)

        result = await client.chat_with_mcp(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="hello")],
            mcp_engine=engine,
            active_servers=["demo"],
        )

        assert result.content == "Done with MCP help"
        engine.chat_with_mcp.assert_awaited_once()

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_chat_auto_detection_switches_between_providers(
        self, mock_openai, mock_anthropic
    ):
        """Test model-based provider auto-detection switches providers per call."""
        openai_client = MagicMock()
        mock_openai.return_value = openai_client
        openai_response = MagicMock()
        openai_response.model_dump.return_value = {
            "id": "openai-test",
            "model": "gpt-4.1-mini",
            "created": 1234567890,
            "choices": [{"message": {"content": "OpenAI hi"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
        openai_client.chat.completions.create = AsyncMock(return_value=openai_response)

        anthropic_client = MagicMock()
        mock_anthropic.return_value = anthropic_client
        anthropic_response = {
            "id": "anthropic-test",
            "model": "claude-3-5-sonnet-20241022",
            "content": [{"type": "text", "text": "Anthropic hi"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        anthropic_client.messages.create = AsyncMock(
            return_value=MagicMock(model_dump=lambda: anthropic_response)
        )

        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]

        response_openai = await client.chat(model="gpt-4.1-mini", messages=messages)
        response_anthropic = await client.chat(
            model="claude-3-5-sonnet-20241022", messages=messages
        )

        assert response_openai.content == "OpenAI hi"
        assert response_anthropic.content == "Anthropic hi"
        assert "openai" in client._providers
        assert "anthropic" in client._providers
        assert client.provider_name == "anthropic"

    @patch("stratifyai.client.APIKeyHelper.validate_api_key")
    def test_client_initialization_fail_fast_api_key_validation(
        self, mock_validate_api_key
    ):
        """Explicit provider should validate auth during client init."""
        mock_validate_api_key.return_value = (False, "missing key")

        with pytest.raises(AuthenticationError):
            LLMClient(provider="openai")

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_client_blocks_invalid_reasoning_temperature(self, mock_openai):
        """Reasoning models must use temperature=1.0 at client layer."""
        mock_openai.return_value = MagicMock()

        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]

        with pytest.raises(ValidationError):
            await client.chat(model="o1", messages=messages, temperature=0.7)

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_chat_completion_retries_provider_errors(self, mock_openai):
        """Non-streaming calls should retry transient provider failures."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        successful_response = MagicMock()
        successful_response.model_dump.return_value = {
            "id": "test",
            "model": "gpt-4.1-mini",
            "created": 1234567890,
            "choices": [{"message": {"content": "Recovered"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                ProviderAPIError("transient", "openai"),
                successful_response,
            ]
        )

        client = LLMClient(
            api_key="test-key", config={"retry": {"max_retries": 1, "jitter": False}}
        )
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
        )

        response = await client.chat_completion(request)

        assert response.content == "Recovered"
        assert mock_client.chat.completions.create.call_count == 2

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_streaming_retries_provider_errors(self, mock_openai):
        """Streaming calls should retry when setup fails with provider errors."""
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        chunk = MagicMock()
        chunk.model_dump.return_value = {
            "id": "stream-test",
            "model": "gpt-4.1-mini",
            "created": 1234567890,
            "choices": [{"delta": {"content": "Hello"}, "finish_reason": None}],
        }
        chunk.choices = [MagicMock(delta=MagicMock(content="Hello"))]

        async def async_iter_chunks():
            yield chunk

        mock_client.chat.completions.create = AsyncMock(
            side_effect=[
                ProviderAPIError("transient stream", "openai"),
                async_iter_chunks(),
            ]
        )

        client = LLMClient(
            api_key="test-key", config={"retry": {"max_retries": 1, "jitter": False}}
        )
        request = ChatRequest(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hello")],
            stream=True,
        )

        chunks = [c async for c in client.chat_completion_stream(request)]

        assert len(chunks) == 1
        assert chunks[0].content == "Hello"
        assert mock_client.chat.completions.create.call_count == 2

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    def test_provider_timeout_override_via_client_config(self, mock_openai):
        """Provider timeout should be configurable per provider."""
        mock_openai.return_value = MagicMock()

        LLMClient(
            provider="openai",
            api_key="test-key",
            config={
                "providers": {
                    "openai": {
                        "timeout_seconds": 12,
                    }
                }
            },
        )

        kwargs = mock_openai.call_args.kwargs
        assert kwargs["timeout"] == 12

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_chat_cancellation_via_cancel_event(self, mock_openai):
        """Client should support cooperative cancellation for long-running calls."""
        mock_openai.return_value = MagicMock()
        cancel_event = asyncio.Event()
        cancel_event.set()

        client = LLMClient(api_key="test-key")
        messages = [Message(role="user", content="Hello")]

        with pytest.raises(asyncio.CancelledError):
            await client.chat(
                model="gpt-4.1-mini",
                messages=messages,
                cancel_event=cancel_event,
            )
