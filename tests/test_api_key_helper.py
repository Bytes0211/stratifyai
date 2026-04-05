"""Additional unit coverage for API key helper utilities."""

from pathlib import Path
from unittest.mock import patch

import pytest

from stratifyai.api_key_helper import (
    APIKeyHelper,
    check_provider_available,
    get_api_key_or_error,
    print_setup_instructions,
)
from stratifyai.exceptions import AuthenticationError


class TestAPIKeyHelper:
    def test_get_api_key_prefers_explicit_value(self):
        assert APIKeyHelper.get_api_key("openai", api_key="direct-key") == "direct-key"

    @patch.dict(
        "os.environ",
        {"OPENAI_API_KEY": "env-openai", "GROK_API_KEY": "legacy-grok"},
        clear=True,
    )
    def test_get_api_key_reads_environment_and_grok_fallback(self):
        assert APIKeyHelper.get_api_key("openai") == "env-openai"
        assert APIKeyHelper.get_api_key("grok") == "legacy-grok"

    @patch.dict("os.environ", {}, clear=True)
    def test_validate_api_key_returns_helpful_message_for_missing_standard_provider(
        self,
    ):
        is_valid, error_message = APIKeyHelper.validate_api_key("openai", api_key=None)

        assert is_valid is False
        assert error_message is not None
        assert "OPENAI_API_KEY" in error_message
        assert "platform.openai.com/api-keys" in error_message

    @patch.dict("os.environ", {}, clear=True)
    def test_validate_api_key_returns_bedrock_specific_guidance(self):
        is_valid, error_message = APIKeyHelper.validate_api_key("bedrock", api_key=None)

        assert is_valid is False
        assert error_message is not None
        assert "AWS_BEARER_TOKEN_BEDROCK" in error_message
        assert "AWS_ACCESS_KEY_ID" in error_message

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "configured-anthropic"}, clear=True)
    def test_get_api_key_or_error_includes_alternative_provider_suggestion(self):
        with pytest.raises(AuthenticationError) as exc:
            get_api_key_or_error("openai")

        assert "Anthropic" in str(exc.value)
        assert "OPENAI_API_KEY" in str(exc.value)

    @patch.dict(
        "os.environ",
        {"OPENAI_API_KEY": "openai-key", "ANTHROPIC_API_KEY": "anthropic-key"},
        clear=True,
    )
    def test_check_available_providers_and_setup_instructions(self):
        available = APIKeyHelper.check_available_providers()
        instructions = APIKeyHelper.get_setup_instructions()

        assert available["openai"] is True
        assert available["anthropic"] is True
        assert available["google"] is False
        assert "StratifyAI API Key Setup" in instructions
        assert "OpenAI" in instructions
        assert "Anthropic" in instructions

    def test_create_env_file_if_missing(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        example = tmp_path / ".env.example"
        example.write_text("OPENAI_API_KEY=example\n", encoding="utf-8")

        assert APIKeyHelper.create_env_file_if_missing() is True
        assert (tmp_path / ".env").read_text(
            encoding="utf-8"
        ) == "OPENAI_API_KEY=example\n"
        assert APIKeyHelper.create_env_file_if_missing() is False

    @patch.dict("os.environ", {"OPENAI_API_KEY": "openai-key"}, clear=True)
    def test_print_setup_instructions_and_check_provider_available(self):
        with patch("rich.console.Console") as mock_console, patch("rich.table.Table"):
            print_setup_instructions()

        assert mock_console.return_value.print.call_count >= 3
        assert check_provider_available("openai") is True
        assert check_provider_available("anthropic") is False
