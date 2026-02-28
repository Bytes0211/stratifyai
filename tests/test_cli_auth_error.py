"""Tests for AuthenticationError handling in CLI."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner
from cli.stratifyai_cli import app
from stratifyai.exceptions import AuthenticationError

runner = CliRunner()


class TestAuthenticationErrorHandling:
    """Test suite for authentication error handling."""
    
    @patch("cli.stratifyai_cli.LLMClient")
    def test_chat_displays_auth_error_with_instructions(self, mock_client_class):
        """Test that chat command displays helpful auth error message."""
        # Mock LLMClient to raise AuthenticationError
        mock_client = Mock()
        mock_client.chat_completion_sync.side_effect = AuthenticationError("grok")
        mock_client_class.return_value = mock_client
        
        # Run command with provider, model, and temperature to avoid interactive prompts
        result = runner.invoke(app, [
            "chat",
            "test message",
            "--provider", "grok",
            "--model", "grok-beta",
            "--temperature", "0.7"
        ])
        
        # Verify exit code indicates error
        assert result.exit_code == 1
        
        # Verify error message components
        assert "Authentication Failed" in result.output
        assert "Provider: grok" in result.output
        assert "API key is missing or invalid" in result.output
        assert "GROK_API_KEY" in result.output
        assert "export GROK_API_KEY" in result.output
        assert ".env file" in result.output
        assert "https://console.x.ai/" in result.output
    
    @patch("cli.stratifyai_cli.LLMClient")
    def test_chat_openai_auth_error(self, mock_client_class):
        """Test OpenAI-specific auth error message."""
        mock_client = Mock()
        mock_client.chat_completion_sync.side_effect = AuthenticationError("openai")
        mock_client_class.return_value = mock_client
        
        result = runner.invoke(app, [
            "chat",
            "test message",
            "--provider", "openai",
            "--model", "gpt-4o",
            "--temperature", "0.7"
        ])
        
        assert result.exit_code == 1
        assert "OPENAI_API_KEY" in result.output
        assert "https://platform.openai.com/api-keys" in result.output
    
    @patch("cli.stratifyai_cli.LLMClient")
    def test_chat_anthropic_auth_error(self, mock_client_class):
        """Test Anthropic-specific auth error message."""
        mock_client = Mock()
        mock_client.chat_completion_sync.side_effect = AuthenticationError("anthropic")
        mock_client_class.return_value = mock_client
        
        result = runner.invoke(app, [
            "chat",
            "test message",
            "--provider", "anthropic",
            "--model", "claude-sonnet-4-5",
            "--temperature", "0.7"
        ])
        
        assert result.exit_code == 1
        assert "ANTHROPIC_API_KEY" in result.output
        assert "https://console.anthropic.com/settings/keys" in result.output
    
    @patch("cli.stratifyai_cli.LLMClient")
    def test_chat_google_auth_error(self, mock_client_class):
        """Test Google-specific auth error message."""
        mock_client = Mock()
        mock_client.chat_completion_sync.side_effect = AuthenticationError("google")
        mock_client_class.return_value = mock_client
        
        result = runner.invoke(app, [
            "chat",
            "test message",
            "--provider", "google",
            "--model", "gemini-2.5-pro",
            "--temperature", "0.7"
        ])
        
        assert result.exit_code == 1
        assert "GOOGLE_API_KEY" in result.output
        assert "https://aistudio.google.com/app/apikey" in result.output
    
    @patch("cli.stratifyai_cli.LLMClient")
    def test_chat_deepseek_auth_error(self, mock_client_class):
        """Test DeepSeek-specific auth error message."""
        mock_client = Mock()
        mock_client.chat_completion_sync.side_effect = AuthenticationError("deepseek")
        mock_client_class.return_value = mock_client
        
        result = runner.invoke(app, [
            "chat",
            "test message",
            "--provider", "deepseek",
            "--model", "deepseek-chat",
            "--temperature", "0.7"
        ])
        
        assert result.exit_code == 1
        assert "DEEPSEEK_API_KEY" in result.output
        assert "https://platform.deepseek.com/api_keys" in result.output
    
    @patch("cli.stratifyai_cli.LLMClient")
    def test_chat_groq_auth_error(self, mock_client_class):
        """Test Groq-specific auth error message."""
        mock_client = Mock()
        mock_client.chat_completion_sync.side_effect = AuthenticationError("groq")
        mock_client_class.return_value = mock_client
        
        result = runner.invoke(app, [
            "chat",
            "test message",
            "--provider", "groq",
            "--model", "llama-3.3-70b-versatile",
            "--temperature", "0.7"
        ])
        
        assert result.exit_code == 1
        assert "GROQ_API_KEY" in result.output
        assert "https://console.groq.com/keys" in result.output
    
    @patch("cli.stratifyai_cli.LLMClient")
    def test_chat_openrouter_auth_error(self, mock_client_class):
        """Test OpenRouter-specific auth error message."""
        mock_client = Mock()
        mock_client.chat_completion_sync.side_effect = AuthenticationError("openrouter")
        mock_client_class.return_value = mock_client
        
        result = runner.invoke(app, [
            "chat",
            "test message",
            "--provider", "openrouter",
            "--model", "anthropic/claude-sonnet-4-5",
            "--temperature", "0.7"
        ])
        
        assert result.exit_code == 1
        assert "OPENROUTER_API_KEY" in result.output
        assert "https://openrouter.ai/keys" in result.output
    
    @patch("cli.stratifyai_cli.LLMClient")
    def test_chat_ollama_auth_error(self, mock_client_class):
        """Test Ollama-specific auth error message."""
        mock_client = Mock()
        mock_client.chat_completion_sync.side_effect = AuthenticationError("ollama")
        mock_client_class.return_value = mock_client
        
        result = runner.invoke(app, [
            "chat",
            "test message",
            "--provider", "ollama",
            "--model", "llama3.2",
            "--temperature", "0.7"
        ])
        
        assert result.exit_code == 1
        assert "OLLAMA_API_KEY" in result.output
        assert "ollama serve" in result.output
    
