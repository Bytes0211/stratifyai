"""Tests for Phase 2 providers (Anthropic, Google, DeepSeek, Groq, Grok, Ollama, OpenRouter)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from llm_abstraction.providers.anthropic import AnthropicProvider
from llm_abstraction.providers.google import GoogleProvider
from llm_abstraction.providers.deepseek import DeepSeekProvider
from llm_abstraction.providers.groq import GroqProvider
from llm_abstraction.providers.grok import GrokProvider
from llm_abstraction.providers.ollama import OllamaProvider
from llm_abstraction.providers.openrouter import OpenRouterProvider
from llm_abstraction.models import ChatRequest, Message
from llm_abstraction.exceptions import AuthenticationError, InvalidModelError


class TestAnthropicProvider:
    """Tests for Anthropic provider."""
    
    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("llm_abstraction.providers.anthropic.Anthropic"):
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
            with patch("llm_abstraction.providers.anthropic.Anthropic"):
                provider = AnthropicProvider()
                assert provider.api_key == "env-key"
    
    def test_supported_models(self):
        """Test that provider returns list of supported models."""
        with patch("llm_abstraction.providers.anthropic.Anthropic"):
            provider = AnthropicProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "claude-3-5-sonnet-20241022" in models
    
    def test_validate_model(self):
        """Test model validation."""
        with patch("llm_abstraction.providers.anthropic.Anthropic"):
            provider = AnthropicProvider(api_key="test-key")
            assert provider.validate_model("claude-3-5-sonnet-20241022") is True
            assert provider.validate_model("invalid-model") is False
    
    @patch("llm_abstraction.providers.anthropic.Anthropic")
    def test_chat_completion(self, mock_anthropic_class):
        """Test chat completion request."""
        # Setup mock
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        mock_response = {
            "id": "msg_123",
            "model": "claude-3-5-sonnet-20241022",
            "content": [{"type": "text", "text": "Hello!"}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
            }
        }
        
        mock_client.messages.create.return_value = Mock(model_dump=lambda: mock_response)
        
        # Create provider and make request
        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[Message(role="user", content="Hello")]
        )
        
        response = provider.chat_completion(request)
        
        assert response.content == "Hello!"
        assert response.provider == "anthropic"
        assert response.usage.prompt_tokens == 10
        assert response.usage.completion_tokens == 5
        assert response.usage.total_tokens == 15
    
    def test_chat_completion_invalid_model(self):
        """Test chat completion with invalid model raises error."""
        with patch("llm_abstraction.providers.anthropic.Anthropic"):
            provider = AnthropicProvider(api_key="test-key")
            request = ChatRequest(
                model="invalid-model",
                messages=[Message(role="user", content="Hello")]
            )
            
            with pytest.raises(InvalidModelError):
                provider.chat_completion(request)


class TestGoogleProvider:
    """Tests for Google Gemini provider."""
    
    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
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
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
            provider = GoogleProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "gemini-2.5-pro" in models


class TestDeepSeekProvider:
    """Tests for DeepSeek provider."""
    
    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
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
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
            provider = DeepSeekProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "deepseek-chat" in models


class TestGroqProvider:
    """Tests for Groq provider."""
    
    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
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
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
            provider = GroqProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "llama-3.1-70b-versatile" in models


class TestGrokProvider:
    """Tests for Grok (X.AI) provider."""
    
    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
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
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
            provider = GrokProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "grok-beta" in models


class TestOllamaProvider:
    """Tests for Ollama provider."""
    
    def test_initialization_without_api_key(self):
        """Test provider initialization works without API key (Ollama doesn't require one)."""
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
            provider = OllamaProvider()
            assert provider.api_key == "ollama"
            assert provider.provider_name == "ollama"
    
    def test_initialization_with_custom_base_url(self):
        """Test provider initialization with custom base URL."""
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
            provider = OllamaProvider(config={"base_url": "http://custom:11434/v1"})
            assert provider.base_url == "http://custom:11434/v1"
    
    def test_supported_models(self):
        """Test that provider returns list of supported models."""
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
            provider = OllamaProvider()
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "llama3.2" in models


class TestOpenRouterProvider:
    """Tests for OpenRouter provider."""
    
    def test_initialization_with_api_key(self):
        """Test provider initialization with API key."""
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
            provider = OpenRouterProvider(api_key="test-key")
            assert provider.api_key == "test-key"
            assert provider.provider_name == "openrouter"
    
    def test_initialization_without_api_key(self):
        """Test provider initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(AuthenticationError):
                OpenRouterProvider()
    
    def test_supported_models(self):
        """Test that provider returns list of supported models."""
        with patch("llm_abstraction.providers.openai_compatible.OpenAI"):
            provider = OpenRouterProvider(api_key="test-key")
            models = provider.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "anthropic/claude-3-5-sonnet" in models
