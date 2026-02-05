"""Unit tests for ChatBuilder pattern."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from stratifyai.chat.builder import ChatBuilder, create_module_builder
from stratifyai.models import ChatResponse, Message, Usage


def create_mock_response(content: str = "Hello!") -> dict:
    """Create a mock OpenAI-style response."""
    return {
        "id": "test-123",
        "model": "gpt-4o-mini",
        "created": 1234567890,
        "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


class TestChatBuilder:
    """Tests for ChatBuilder class."""

    def test_builder_initialization(self):
        """Test ChatBuilder initializes with defaults."""
        builder = ChatBuilder(
            provider="openai",
            default_temperature=0.7,
        )
        assert builder.provider == "openai"
        assert builder.model is None  # No default model
        assert builder.temperature == 0.7

    def test_with_model_returns_new_builder(self):
        """Test with_model returns a new ChatBuilder instance."""
        builder = ChatBuilder(provider="openai")
        new_builder = builder.with_model("gpt-4.1")
        
        # Original unchanged
        assert builder.model is None
        assert builder._model is None
        
        # New builder has model set
        assert new_builder.model == "gpt-4.1"
        assert new_builder._model == "gpt-4.1"

    def test_with_system_returns_new_builder(self):
        """Test with_system returns a new ChatBuilder instance."""
        builder = ChatBuilder(provider="openai")
        new_builder = builder.with_system("You are helpful")
        
        assert builder._system is None
        assert new_builder._system == "You are helpful"

    def test_with_developer_returns_new_builder(self):
        """Test with_developer returns a new ChatBuilder instance."""
        builder = ChatBuilder(provider="openai")
        new_builder = builder.with_developer("Use markdown")
        
        assert builder._developer is None
        assert new_builder._developer == "Use markdown"

    def test_with_temperature_returns_new_builder(self):
        """Test with_temperature returns a new ChatBuilder instance."""
        builder = ChatBuilder(
            provider="openai",
            default_temperature=0.7,
        )
        new_builder = builder.with_temperature(0.3)
        
        assert builder.temperature == 0.7
        assert new_builder.temperature == 0.3

    def test_with_max_tokens_returns_new_builder(self):
        """Test with_max_tokens returns a new ChatBuilder instance."""
        builder = ChatBuilder(provider="openai")
        new_builder = builder.with_max_tokens(500)
        
        assert builder.max_tokens is None
        assert new_builder.max_tokens == 500

    def test_with_options_returns_new_builder(self):
        """Test with_options returns a new ChatBuilder instance."""
        builder = ChatBuilder(provider="openai")
        new_builder = builder.with_options(top_p=0.9, frequency_penalty=0.5)
        
        assert builder._extra_kwargs == {}
        assert new_builder._extra_kwargs == {"top_p": 0.9, "frequency_penalty": 0.5}


class TestChatBuilderChaining:
    """Tests for builder method chaining."""

    def test_chain_multiple_methods(self):
        """Test chaining multiple builder methods."""
        builder = ChatBuilder(
            provider="anthropic",
            default_temperature=0.7,
        )
        
        configured = (
            builder
            .with_model("claude-opus-4-5")
            .with_system("You are a coding assistant")
            .with_developer("Use markdown formatting")
            .with_temperature(0.5)
            .with_max_tokens(1000)
        )
        
        # Original unchanged
        assert builder.model is None
        assert builder._system is None
        assert builder._developer is None
        assert builder.temperature == 0.7
        assert builder.max_tokens is None
        
        # Configured builder has all settings
        assert configured.model == "claude-opus-4-5"
        assert configured._system == "You are a coding assistant"
        assert configured._developer == "Use markdown formatting"
        assert configured.temperature == 0.5
        assert configured.max_tokens == 1000

    def test_chain_preserves_provider(self):
        """Test that chaining preserves the provider."""
        builder = ChatBuilder(provider="google")
        configured = builder.with_model("gemini-2.5-pro").with_temperature(0.3)
        
        assert configured.provider == "google"


class TestChatBuilderSystemPrompt:
    """Tests for system and developer prompt building."""

    def test_build_system_prompt_system_only(self):
        """Test system prompt building with system only."""
        builder = ChatBuilder(
            provider="openai",
        ).with_system("You are helpful")
        
        assert builder._build_system_prompt() == "You are helpful"

    def test_build_system_prompt_developer_only(self):
        """Test system prompt building with developer only."""
        builder = ChatBuilder(
            provider="openai",
        ).with_developer("Use markdown")
        
        assert builder._build_system_prompt() == "Use markdown"

    def test_build_system_prompt_both(self):
        """Test system prompt building with both developer and system."""
        builder = ChatBuilder(
            provider="openai",
        ).with_system("You are helpful").with_developer("Use markdown")
        
        expected = "Use markdown\n\nYou are helpful"
        assert builder._build_system_prompt() == expected

    def test_build_system_prompt_none(self):
        """Test system prompt building with neither set."""
        builder = ChatBuilder(provider="openai")
        assert builder._build_system_prompt() is None


class TestChatBuilderMessages:
    """Tests for message building."""

    def test_build_messages_string_prompt(self):
        """Test building messages from string prompt."""
        builder = ChatBuilder(provider="openai")
        messages = builder._build_messages("Hello!")
        
        assert len(messages) == 1
        assert messages[0].role == "user"
        assert messages[0].content == "Hello!"

    def test_build_messages_with_system(self):
        """Test building messages with system prompt."""
        builder = ChatBuilder(
            provider="openai",
        ).with_system("Be helpful")
        
        messages = builder._build_messages("Hello!")
        
        assert len(messages) == 2
        assert messages[0].role == "system"
        assert messages[0].content == "Be helpful"
        assert messages[1].role == "user"
        assert messages[1].content == "Hello!"

    def test_build_messages_list_prompt(self):
        """Test building messages from list of Message objects."""
        builder = ChatBuilder(provider="openai")
        input_messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
        ]
        
        messages = builder._build_messages(input_messages)
        
        assert len(messages) == 3
        assert messages[0].content == "Hello"
        assert messages[1].content == "Hi there!"
        assert messages[2].content == "How are you?"


class TestChatBuilderAsyncChat:
    """Tests for async chat method."""

    @pytest.mark.asyncio
    async def test_chat_with_configured_model(self):
        """Test chat uses configured model."""
        # Create mock LLMClient instance
        mock_client = MagicMock()
        mock_response = ChatResponse(
            id="test-123",
            model="gpt-4.1",
            content="Hello!",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
        )
        mock_client.chat = AsyncMock(return_value=mock_response)
        
        # Create builder with mock client factory - must use with_model
        builder = create_module_builder(
            provider="openai",
            client_factory=lambda: mock_client,
        ).with_model("gpt-4.1")
        
        response = await builder.chat("Hello")
        
        # Verify model was passed correctly
        call_args = mock_client.chat.call_args
        assert call_args[1]["model"] == "gpt-4.1"

    @pytest.mark.asyncio
    async def test_chat_with_configured_temperature(self):
        """Test chat uses configured temperature."""
        mock_client = MagicMock()
        mock_response = ChatResponse(
            id="test-123",
            model="gpt-4o-mini",
            content="Hello!",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
        )
        mock_client.chat = AsyncMock(return_value=mock_response)
        
        # Must specify model
        builder = create_module_builder(
            provider="openai",
            client_factory=lambda: mock_client,
        ).with_model("gpt-4o-mini").with_temperature(0.3)
        
        response = await builder.chat("Hello")
        
        call_args = mock_client.chat.call_args
        assert call_args[1]["temperature"] == 0.3

    @pytest.mark.asyncio
    async def test_chat_override_configured_model(self):
        """Test chat can override configured model."""
        mock_client = MagicMock()
        mock_response = ChatResponse(
            id="test-123",
            model="gpt-4.1-mini",
            content="Hello!",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
        )
        mock_client.chat = AsyncMock(return_value=mock_response)
        
        builder = create_module_builder(
            provider="openai",
            client_factory=lambda: mock_client,
        ).with_model("gpt-4.1")
        
        # Override with different model
        response = await builder.chat("Hello", model="gpt-4.1-mini")
        
        call_args = mock_client.chat.call_args
        assert call_args[1]["model"] == "gpt-4.1-mini"

    @pytest.mark.asyncio
    async def test_chat_without_model_raises_error(self):
        """Test chat raises error when no model specified."""
        mock_client = MagicMock()
        
        builder = create_module_builder(
            provider="openai",
            client_factory=lambda: mock_client,
        )
        
        with pytest.raises(ValueError, match="Model is required"):
            await builder.chat("Hello")


class TestModuleLevelBuilder:
    """Tests for module-level builder functions."""

    def test_create_module_builder(self):
        """Test create_module_builder creates configured builder."""
        builder = create_module_builder(
            provider="anthropic",
            default_temperature=0.8,
            default_max_tokens=2000,
        )
        
        assert builder.provider == "anthropic"
        assert builder.model is None  # No default model
        assert builder.default_temperature == 0.8
        assert builder.default_max_tokens == 2000

    def test_module_builder_with_client_factory(self):
        """Test builder uses client factory when provided."""
        mock_client = MagicMock()
        factory = MagicMock(return_value=mock_client)
        
        builder = create_module_builder(
            provider="openai",
            client_factory=factory,
        )
        
        client = builder._get_client()
        factory.assert_called_once()
        assert client == mock_client


class TestProviderModuleBuilder:
    """Tests for provider module builder integration."""

    def test_openai_module_has_builder_methods(self):
        """Test openai module exposes builder methods."""
        from stratifyai.chat import stratifyai_openai as openai
        
        assert hasattr(openai, "with_model")
        assert hasattr(openai, "with_system")
        assert hasattr(openai, "with_developer")
        assert hasattr(openai, "with_temperature")
        assert hasattr(openai, "with_max_tokens")
        assert hasattr(openai, "with_options")

    def test_anthropic_module_has_builder_methods(self):
        """Test anthropic module exposes builder methods."""
        from stratifyai.chat import stratifyai_anthropic as anthropic
        
        assert hasattr(anthropic, "with_model")
        assert hasattr(anthropic, "with_system")
        assert hasattr(anthropic, "with_developer")

    def test_openai_with_model_returns_builder(self):
        """Test openai.with_model returns ChatBuilder."""
        from stratifyai.chat import stratifyai_openai as openai
        
        builder = openai.with_model("gpt-4.1")
        assert isinstance(builder, ChatBuilder)
        assert builder.model == "gpt-4.1"

    def test_anthropic_with_system_returns_builder(self):
        """Test anthropic.with_system returns ChatBuilder."""
        from stratifyai.chat import stratifyai_anthropic as anthropic
        
        builder = anthropic.with_system("Be helpful")
        assert isinstance(builder, ChatBuilder)
        assert builder._system == "Be helpful"

    def test_builder_chaining_from_module(self):
        """Test builder chaining works from module."""
        from stratifyai.chat import stratifyai_openai as openai
        
        builder = (
            openai
            .with_model("gpt-4.1")
            .with_system("You are helpful")
            .with_developer("Use markdown")
            .with_temperature(0.5)
        )
        
        assert isinstance(builder, ChatBuilder)
        assert builder.model == "gpt-4.1"
        assert builder._system == "You are helpful"
        assert builder._developer == "Use markdown"
        assert builder.temperature == 0.5


class TestChatBuilderExport:
    """Tests for ChatBuilder export from package."""

    def test_chatbuilder_exported_from_chat_package(self):
        """Test ChatBuilder is exported from stratifyai.chat."""
        from stratifyai.chat import ChatBuilder
        
        builder = ChatBuilder(provider="openai")
        assert builder.provider == "openai"
        assert builder.model is None  # No default model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
