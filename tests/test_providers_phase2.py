"""Tests for Phase 2 providers (Anthropic, Google, DeepSeek, Groq, Grok, Ollama, OpenRouter)."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from stratifyai.exceptions import (
    AuthenticationError,
    InvalidModelError,
    ProviderAPIError,
)
from stratifyai.models import ChatRequest, Message
from stratifyai.providers.anthropic import AnthropicProvider
from stratifyai.providers.deepseek import DeepSeekProvider
from stratifyai.providers.google import GoogleProvider
from stratifyai.providers.grok import GrokProvider
from stratifyai.providers.groq import GroqProvider
from stratifyai.providers.ollama import OllamaProvider
from stratifyai.providers.openrouter import OpenRouterProvider


class TestAnthropicProvider:
    """Tests for Anthropic provider."""

    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("stratifyai.providers.anthropic.AsyncAnthropic"):
            provider = AnthropicProvider(api_key="test-key")
            assert provider.api_key == "test-key"
            assert provider.provider_name == "anthropic"

    def test_initialization_without_api_key(self):
        """Test provider initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthenticationError):
                AnthropicProvider()

    def test_initialization_with_env_var(self):
        """Test provider initialization with environment variable."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "env-key"}):
            with patch("stratifyai.providers.anthropic.AsyncAnthropic"):
                provider = AnthropicProvider()
                assert provider.api_key == "env-key"

    def test_supported_models(self):
        """Test that provider returns list of supported models."""
        with patch("stratifyai.providers.anthropic.AsyncAnthropic"):
            provider = AnthropicProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "claude-3-5-sonnet-20241022" in models

    def test_validate_model(self):
        """Test model validation."""
        with patch("stratifyai.providers.anthropic.AsyncAnthropic"):
            provider = AnthropicProvider(api_key="test-key")
            assert provider.validate_model("claude-3-5-sonnet-20241022") is True
            assert provider.validate_model("invalid-model") is False

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_chat_completion(self, mock_anthropic_class):
        """Test chat completion request."""
        # Setup mock
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = {
            "id": "msg_123",
            "model": "claude-3-5-sonnet-20241022",
            "content": [{"type": "text", "text": "Hello!"}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
            },
        }

        mock_client.messages.create = AsyncMock(
            return_value=Mock(model_dump=lambda: mock_response)
        )

        # Create provider and make request
        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[Message(role="user", content="Hello")],
        )

        response = await provider.chat_completion(request)

        assert response.content == "Hello!"
        assert response.provider == "anthropic"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 5
        assert response.usage.total_tokens == 15

    @pytest.mark.asyncio
    async def test_chat_completion_invalid_model(self):
        """Test chat completion with invalid model raises error."""
        with patch("stratifyai.providers.anthropic.AsyncAnthropic"):
            provider = AnthropicProvider(api_key="test-key")
            request = ChatRequest(
                model="invalid-model", messages=[Message(role="user", content="Hello")]
            )

            with pytest.raises(InvalidModelError):
                await provider.chat_completion(request)

    def test_normalize_response_clamps_negative_non_cached_tokens(self):
        """Cache reads larger than prompt tokens must not produce negative base cost."""
        with patch("stratifyai.providers.anthropic.AsyncAnthropic"):
            provider = AnthropicProvider(api_key="test-key")
            response = provider._normalize_response(
                {
                    "id": "msg_cached",
                    "model": "claude-3-5-sonnet-20241022",
                    "content": [{"type": "text", "text": "cached"}],
                    "stop_reason": "end_turn",
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 0,
                        "cache_read_input_tokens": 250,
                    },
                }
            )

            breakdown = response.usage.cost_breakdown
            assert breakdown is not None
            assert breakdown["base_cost"] == 0.0
            assert response.usage.cost_usd == breakdown["cache_cost"]

    def test_normalize_response_rejects_missing_content_blocks(self):
        with patch("stratifyai.providers.anthropic.AsyncAnthropic"):
            provider = AnthropicProvider(api_key="test-key")
            with pytest.raises(ProviderAPIError, match="missing content"):
                provider._normalize_response(
                    {
                        "id": "msg_invalid",
                        "model": "claude-3-5-sonnet-20241022",
                        "stop_reason": "end_turn",
                        "usage": {"input_tokens": 1, "output_tokens": 1},
                    }
                )


class TestGoogleProvider:
    """Tests for Google Gemini provider."""

    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = GoogleProvider(api_key="test-key")
            assert provider.api_key == "test-key"
            assert provider.provider_name == "google"

    def test_initialization_without_api_key(self):
        """Test provider initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthenticationError):
                GoogleProvider()

    def test_supported_models(self):
        """Test that provider returns list of supported models."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = GoogleProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "gemini-2.5-pro" in models


class TestDeepSeekProvider:
    """Tests for DeepSeek provider."""

    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = DeepSeekProvider(api_key="test-key")
            assert provider.api_key == "test-key"
            assert provider.provider_name == "deepseek"

    def test_initialization_without_api_key(self):
        """Test provider initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthenticationError):
                DeepSeekProvider()

    def test_supported_models(self):
        """Test that provider returns list of supported models."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = DeepSeekProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "deepseek-chat" in models


class TestGroqProvider:
    """Tests for Groq provider."""

    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = GroqProvider(api_key="test-key")
            assert provider.api_key == "test-key"
            assert provider.provider_name == "groq"

    def test_initialization_without_api_key(self):
        """Test provider initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthenticationError):
                GroqProvider()

    def test_supported_models(self):
        """Test that provider returns list of supported models."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = GroqProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "llama-3.1-70b-versatile" in models


class TestGrokProvider:
    """Tests for Grok (X.AI) provider."""

    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = GrokProvider(api_key="test-key")
            assert provider.api_key == "test-key"
            assert provider.provider_name == "grok"

    def test_initialization_without_api_key(self):
        """Test provider initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthenticationError):
                GrokProvider()

    def test_supported_models(self):
        """Test that provider returns list of supported models."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = GrokProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "grok-beta" in models


class TestOllamaProvider:
    """Tests for Ollama provider."""

    def test_initialization_without_api_key(self):
        """Test provider initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthenticationError):
                OllamaProvider()

    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = OllamaProvider(api_key="test-key")
            assert provider.api_key == "test-key"
            assert provider.provider_name == "ollama"

    def test_initialization_with_custom_base_url(self):
        """Test provider initialization with custom base URL."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = OllamaProvider(
                api_key="test-key", config={"base_url": "http://custom:11434/v1"}
            )
            assert provider.base_url == "http://custom:11434/v1"

    def test_supported_models(self):
        """Test that provider returns list of supported models."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = OllamaProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "llama3.2" in models


class TestOpenRouterProvider:
    """Tests for OpenRouter provider."""

    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = OpenRouterProvider(api_key="test-key")
            assert provider.api_key == "test-key"
            assert provider.provider_name == "openrouter"

    def test_initialization_without_api_key(self):
        """Test provider initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthenticationError):
                OpenRouterProvider()

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_streaming_uses_top_p_without_temperature_when_top_p_set(
        self, mock_anthropic_class
    ):
        """Test Anthropic streaming uses top_p only when top_p is explicitly set."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        stream_ctx = MagicMock()
        stream_ctx.__aenter__ = AsyncMock(return_value=stream_ctx)
        stream_ctx.__aexit__ = AsyncMock(return_value=None)

        async def text_stream_gen():
            yield "hello"

        stream_ctx.text_stream = text_stream_gen()
        mock_client.messages.stream.return_value = stream_ctx

        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[Message(role="user", content="Hello")],
            top_p=0.9,
        )

        chunks = [chunk async for chunk in provider.chat_completion_stream(request)]
        assert len(chunks) == 1

        kwargs = mock_client.messages.stream.call_args.kwargs
        assert kwargs["top_p"] == 0.9
        assert "temperature" not in kwargs

    def test_supported_models(self):
        """Test that provider returns list of supported models."""
        with patch("stratifyai.providers.openai_compatible.AsyncOpenAI"):
            provider = OpenRouterProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "anthropic/claude-3-5-sonnet" in models
