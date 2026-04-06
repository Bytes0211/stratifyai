"""Unit tests for provider model validation utilities."""

from unittest.mock import MagicMock, patch

from stratifyai.utils.provider_validator import (
    _validate_anthropic,
    _validate_bedrock,
    _validate_google,
    _validate_ollama,
    _validate_openai,
    _validate_openai_compatible,
    _validate_openrouter,
    get_validated_interactive_models,
    validate_provider_models,
)


class TestProviderValidator:
    def test_unknown_provider_returns_error(self):
        result = validate_provider_models("unknown", ["model-a"])

        assert result["error"] == "No validator for provider: unknown"
        assert result["valid_models"] == ["model-a"]

    @patch("openai.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-openai"}, clear=True)
    def test_validate_openai_uses_models_list(self, mock_openai):
        client = MagicMock()
        client.models.list.return_value = MagicMock(data=[MagicMock(id="gpt-4o-mini")])
        mock_openai.return_value = client

        result = _validate_openai(["gpt-4o-mini", "missing-model"])

        assert result["valid_models"] == ["gpt-4o-mini"]
        assert result["invalid_models"] == ["missing-model"]

    @patch("anthropic.Anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True)
    def test_validate_anthropic_falls_back_for_old_sdk(self, mock_anthropic):
        client = MagicMock()
        client.models.list.side_effect = AttributeError("old sdk")
        mock_anthropic.return_value = client

        result = _validate_anthropic(["claude-3-5-sonnet-20241022"])

        assert result["valid_models"] == ["claude-3-5-sonnet-20241022"]
        assert "SDK too old" in result["error"]

    @patch("google.genai.Client")
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "google-key"}, clear=True)
    def test_validate_google_matches_model_names(self, mock_client_class):
        client = MagicMock()
        client.models.list.return_value = [MagicMock(name="models/gemini-2.5-flash")]
        mock_client_class.return_value = client

        result = _validate_google(["gemini-2.5-flash", "missing-model"])

        assert result["valid_models"] == ["gemini-2.5-flash"]
        assert result["invalid_models"] == ["missing-model"]

    @patch("httpx.Client")
    @patch.dict("os.environ", {"DEEPSEEK_API_KEY": "deepseek-key"}, clear=True)
    def test_validate_openai_compatible_reads_model_ids(self, mock_client_class):
        response = MagicMock()
        response.json.return_value = {"data": [{"id": "deepseek-chat"}]}
        response.raise_for_status.return_value = None

        client_cm = MagicMock()
        client_cm.__enter__.return_value.get.return_value = response
        client_cm.__exit__.return_value = None
        mock_client_class.return_value = client_cm

        result = _validate_openai_compatible(
            ["deepseek-chat", "missing"],
            "https://api.deepseek.com/v1",
            None,
            "DEEPSEEK_API_KEY",
        )

        assert result["valid_models"] == ["deepseek-chat"]
        assert result["invalid_models"] == ["missing"]

    @patch("httpx.Client")
    def test_validate_ollama_handles_connection_errors(self, mock_client_class):
        client_cm = MagicMock()
        client_cm.__enter__.return_value.get.side_effect = Exception(
            "Connection refused"
        )
        client_cm.__exit__.return_value = None
        mock_client_class.return_value = client_cm

        result = _validate_ollama(["llama3.2"])

        assert "Ollama not running" in result["error"]
        assert result["valid_models"] == ["llama3.2"]

    @patch("stratifyai.utils.provider_validator.validate_bedrock_models")
    def test_validate_bedrock_delegates(self, mock_validate):
        mock_validate.return_value = {
            "valid_models": ["bedrock-model"],
            "invalid_models": [],
            "validation_time_ms": 1,
            "error": None,
        }

        result = _validate_bedrock(["bedrock-model"])

        assert result["valid_models"] == ["bedrock-model"]

    @patch("stratifyai.utils.provider_validator.validate_provider_models")
    def test_get_validated_interactive_models_merges_metadata(self, mock_validate):
        mock_validate.return_value = {
            "valid_models": ["gpt-4o-mini"],
            "invalid_models": [],
            "validation_time_ms": 1,
            "error": None,
        }

        result = get_validated_interactive_models("openai")

        assert "gpt-4o-mini" in result["models"]
        assert result["validation_result"]["valid_models"] == ["gpt-4o-mini"]

    @patch.dict("os.environ", {}, clear=True)
    def test_validate_openai_without_key_returns_config_error(self):
        result = _validate_openai(["gpt-4o-mini"])

        assert result["error"] == "OPENAI_API_KEY not configured"
        assert result["valid_models"] == ["gpt-4o-mini"]
        assert result["invalid_models"] == []

    @patch.dict("os.environ", {}, clear=True)
    def test_validate_google_without_key_returns_config_error(self):
        result = _validate_google(["gemini-2.5-flash"])

        assert result["error"] == "GOOGLE_API_KEY not configured"
        assert result["valid_models"] == ["gemini-2.5-flash"]

    def test_validate_openai_compatible_without_key_returns_config_error(self):
        result = _validate_openai_compatible(
            ["demo-model"],
            "https://example.com/v1",
            None,
            "DEMO_API_KEY",
        )

        assert result["error"] == "DEMO_API_KEY not configured"
        assert result["valid_models"] == ["demo-model"]

    @patch("httpx.Client")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "router-key"}, clear=True)
    def test_validate_openrouter_matches_available_models(self, mock_client_class):
        response = MagicMock()
        response.json.return_value = {"data": [{"id": "openai/gpt-4o-mini"}]}
        response.raise_for_status.return_value = None

        client_cm = MagicMock()
        client_cm.__enter__.return_value.get.return_value = response
        client_cm.__exit__.return_value = None
        mock_client_class.return_value = client_cm

        result = _validate_openrouter(["openai/gpt-4o-mini", "missing-model"])

        assert result["valid_models"] == ["openai/gpt-4o-mini"]
        assert result["invalid_models"] == ["missing-model"]
        assert result["error"] is None

    @patch("httpx.Client")
    def test_validate_ollama_success_matches_tagged_names(self, mock_client_class):
        response = MagicMock()
        response.json.return_value = {
            "models": [
                {"name": "llama3.2:latest"},
                {"name": "codellama"},
            ]
        }
        response.raise_for_status.return_value = None

        client_cm = MagicMock()
        client_cm.__enter__.return_value.get.return_value = response
        client_cm.__exit__.return_value = None
        mock_client_class.return_value = client_cm

        result = _validate_ollama(["llama3.2", "codellama", "missing"])

        assert result["valid_models"] == ["llama3.2", "codellama"]
        assert result["invalid_models"] == ["missing"]
        assert result["error"] is None

    @patch("stratifyai.utils.provider_validator._validate_openai_compatible")
    @patch.dict(
        "os.environ",
        {"XAI_API_KEY": "xai-key", "GROK_API_KEY": "legacy-key"},
        clear=True,
    )
    def test_validate_grok_prefers_xai_api_key(self, mock_validate_compatible):
        mock_validate_compatible.return_value = {
            "valid_models": ["grok-4"],
            "invalid_models": [],
            "validation_time_ms": 1,
            "error": None,
        }

        result = validate_provider_models("grok", ["grok-4"])

        assert result["valid_models"] == ["grok-4"]
        mock_validate_compatible.assert_called_once_with(
            ["grok-4"],
            "https://api.x.ai/v1",
            "xai-key",
            "XAI_API_KEY",
        )

    def test_get_validated_interactive_models_unknown_provider_returns_empty(self):
        result = get_validated_interactive_models("unknown-provider")

        assert result["models"] == {}
        assert (
            result["validation_result"]["error"] == "Unknown provider: unknown-provider"
        )

    @patch("stratifyai.utils.provider_validator.validate_provider_models")
    def test_get_validated_interactive_models_all_models_uses_full_catalog(
        self, mock_validate
    ):
        mock_validate.return_value = {
            "valid_models": ["gpt-4o-mini"],
            "invalid_models": [],
            "validation_time_ms": 1,
            "error": None,
        }

        result = get_validated_interactive_models("openai", all_models=True)

        assert "gpt-4o-mini" in result["models"]
        assert mock_validate.call_args.args[0] == "openai"
        assert isinstance(mock_validate.call_args.args[1], list)
        assert len(mock_validate.call_args.args[1]) >= 1
