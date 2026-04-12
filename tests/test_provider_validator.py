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


# ---------------------------------------------------------------------------
# OpenAI error paths (lines 83-88)
# ---------------------------------------------------------------------------


class TestOpenAIErrorPaths:
    @patch("openai.OpenAI")
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_validate_openai_generic_exception(self, mock_openai):
        mock_openai.return_value.models.list.side_effect = RuntimeError("API down")

        result = _validate_openai(["gpt-4o-mini"])

        assert "Validation failed" in result["error"]
        assert result["valid_models"] == ["gpt-4o-mini"]
        assert result["validation_time_ms"] >= 0

    def test_validate_openai_import_error(self):
        with patch.dict("sys.modules", {"openai": None}):
            result = _validate_openai(["gpt-4o-mini"])

        assert "not installed" in result["error"]
        assert result["valid_models"] == ["gpt-4o-mini"]


# ---------------------------------------------------------------------------
# Anthropic paths (lines 107-121, 131-139)
# ---------------------------------------------------------------------------


class TestAnthropicPaths:
    @patch.dict("os.environ", {}, clear=True)
    def test_validate_anthropic_missing_key(self):
        result = _validate_anthropic(["claude-3-5-sonnet-20241022"])

        assert result["error"] == "ANTHROPIC_API_KEY not configured"
        assert result["valid_models"] == ["claude-3-5-sonnet-20241022"]

    @patch("anthropic.Anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True)
    def test_validate_anthropic_success(self, mock_anthropic):
        client = MagicMock()
        client.models.list.return_value = MagicMock(
            data=[MagicMock(id="claude-3-5-sonnet-20241022")]
        )
        mock_anthropic.return_value = client

        result = _validate_anthropic(["claude-3-5-sonnet-20241022", "missing-model"])

        assert result["valid_models"] == ["claude-3-5-sonnet-20241022"]
        assert result["invalid_models"] == ["missing-model"]
        assert result["error"] is None

    @patch("anthropic.Anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "bad-key"}, clear=True)
    def test_validate_anthropic_old_sdk_invalid_key_format(self, mock_anthropic):
        client = MagicMock()
        client.models.list.side_effect = AttributeError("old sdk")
        mock_anthropic.return_value = client

        result = _validate_anthropic(["claude-3-5-sonnet-20241022"])

        assert "Invalid API key format" in result["error"]
        assert result["valid_models"] == ["claude-3-5-sonnet-20241022"]

    def test_validate_anthropic_import_error(self):
        with patch.dict("sys.modules", {"anthropic": None}):
            result = _validate_anthropic(["claude-3-5-sonnet-20241022"])

        assert "not installed" in result["error"]
        assert result["valid_models"] == ["claude-3-5-sonnet-20241022"]

    @patch("anthropic.Anthropic")
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant-test"}, clear=True)
    def test_validate_anthropic_generic_exception(self, mock_anthropic):
        mock_anthropic.side_effect = RuntimeError("connection error")

        result = _validate_anthropic(["claude-3-5-sonnet-20241022"])

        assert "Validation failed" in result["error"]
        assert result["valid_models"] == ["claude-3-5-sonnet-20241022"]


# ---------------------------------------------------------------------------
# Google edge cases (lines 174, 178, 194-199)
# ---------------------------------------------------------------------------


class TestGoogleEdgeCases:
    @patch("google.genai.Client")
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "google-key"}, clear=True)
    def test_validate_google_non_string_name_skipped(self, mock_client_class):
        """Model with non-string name attribute is skipped."""
        bad_model = MagicMock()
        bad_model.name = 12345  # not a string
        del bad_model._mock_name  # no fallback either

        client = MagicMock()
        client.models.list.return_value = [bad_model]
        mock_client_class.return_value = client

        result = _validate_google(["gemini-2.5-flash"])

        assert result["invalid_models"] == ["gemini-2.5-flash"]

    @patch("google.genai.Client")
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "google-key"}, clear=True)
    def test_validate_google_empty_name_skipped(self, mock_client_class):
        """Model whose name resolves to empty string is skipped."""
        model = MagicMock()
        model.name = "models/"  # resolves to empty after replace

        client = MagicMock()
        client.models.list.return_value = [model]
        mock_client_class.return_value = client

        result = _validate_google(["gemini-2.5-flash"])

        assert result["invalid_models"] == ["gemini-2.5-flash"]

    def test_validate_google_import_error(self):
        with patch.dict("sys.modules", {"google": None, "google.genai": None}):
            result = _validate_google(["gemini-2.5-flash"])

        assert "not installed" in result["error"]
        assert result["valid_models"] == ["gemini-2.5-flash"]

    @patch("google.genai.Client")
    @patch.dict("os.environ", {"GOOGLE_API_KEY": "google-key"}, clear=True)
    def test_validate_google_generic_exception(self, mock_client_class):
        mock_client_class.side_effect = RuntimeError("quota exceeded")

        result = _validate_google(["gemini-2.5-flash"])

        assert "Validation failed" in result["error"]
        assert result["valid_models"] == ["gemini-2.5-flash"]


# ---------------------------------------------------------------------------
# OpenAI-compatible error paths (lines 243-248)
# ---------------------------------------------------------------------------


class TestOpenAICompatibleErrorPaths:
    def test_validate_compatible_import_error(self):
        with patch.dict("sys.modules", {"httpx": None}):
            result = _validate_openai_compatible(
                ["model-a"], "https://example.com/v1", None, "DEMO_KEY"
            )

        assert "not installed" in result["error"]
        assert result["valid_models"] == ["model-a"]

    @patch("httpx.Client")
    @patch.dict("os.environ", {"DEMO_KEY": "test-key"}, clear=True)
    def test_validate_compatible_generic_exception(self, mock_client_class):
        client_cm = MagicMock()
        client_cm.__enter__.return_value.get.side_effect = RuntimeError("timeout")
        client_cm.__exit__.return_value = None
        mock_client_class.return_value = client_cm

        result = _validate_openai_compatible(
            ["model-a"], "https://example.com/v1", None, "DEMO_KEY"
        )

        assert "Validation failed" in result["error"]
        assert result["valid_models"] == ["model-a"]


# ---------------------------------------------------------------------------
# DeepSeek / Groq delegation (lines 259, 269)
# ---------------------------------------------------------------------------


class TestDelegationWrappers:
    @patch("stratifyai.utils.provider_validator._validate_openai_compatible")
    def test_validate_deepseek_delegates(self, mock_validate):
        mock_validate.return_value = {
            "valid_models": ["deepseek-chat"],
            "invalid_models": [],
            "validation_time_ms": 1,
            "error": None,
        }
        result = validate_provider_models("deepseek", ["deepseek-chat"])
        assert result["valid_models"] == ["deepseek-chat"]
        mock_validate.assert_called_once()

    @patch("stratifyai.utils.provider_validator._validate_openai_compatible")
    def test_validate_groq_delegates(self, mock_validate):
        mock_validate.return_value = {
            "valid_models": ["llama-3.3-70b-versatile"],
            "invalid_models": [],
            "validation_time_ms": 1,
            "error": None,
        }
        result = validate_provider_models("groq", ["llama-3.3-70b-versatile"])
        assert result["valid_models"] == ["llama-3.3-70b-versatile"]
        mock_validate.assert_called_once()


# ---------------------------------------------------------------------------
# OpenRouter error paths (lines 301-303, 326-331)
# ---------------------------------------------------------------------------


class TestOpenRouterErrorPaths:
    @patch.dict("os.environ", {}, clear=True)
    def test_validate_openrouter_missing_key(self):
        result = _validate_openrouter(["openai/gpt-4o-mini"])

        assert result["error"] == "OPENROUTER_API_KEY not configured"
        assert result["valid_models"] == ["openai/gpt-4o-mini"]

    def test_validate_openrouter_import_error(self):
        with patch.dict("sys.modules", {"httpx": None}):
            result = _validate_openrouter(["openai/gpt-4o-mini"])

        assert "not installed" in result["error"]
        assert result["valid_models"] == ["openai/gpt-4o-mini"]

    @patch("httpx.Client")
    @patch.dict("os.environ", {"OPENROUTER_API_KEY": "key"}, clear=True)
    def test_validate_openrouter_generic_exception(self, mock_client_class):
        client_cm = MagicMock()
        client_cm.__enter__.return_value.get.side_effect = RuntimeError("down")
        client_cm.__exit__.return_value = None
        mock_client_class.return_value = client_cm

        result = _validate_openrouter(["openai/gpt-4o-mini"])

        assert "Validation failed" in result["error"]
        assert result["valid_models"] == ["openai/gpt-4o-mini"]


# ---------------------------------------------------------------------------
# Ollama non-connection error (lines 371-372, 378)
# ---------------------------------------------------------------------------


class TestOllamaErrorPaths:
    @patch("httpx.Client")
    def test_validate_ollama_generic_non_connection_error(self, mock_client_class):
        client_cm = MagicMock()
        client_cm.__enter__.return_value.get.side_effect = RuntimeError(
            "unexpected error"
        )
        client_cm.__exit__.return_value = None
        mock_client_class.return_value = client_cm

        result = _validate_ollama(["llama3.2"])

        assert "Validation failed" in result["error"]
        assert "Ollama not running" not in result["error"]
        assert result["valid_models"] == ["llama3.2"]

    def test_validate_ollama_import_error(self):
        with patch.dict("sys.modules", {"httpx": None}):
            result = _validate_ollama(["llama3.2"])

        assert "not installed" in result["error"]
        assert result["valid_models"] == ["llama3.2"]
