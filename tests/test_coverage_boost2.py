"""Coverage-boost tests for Anthropic/Bedrock providers and mcp_catalog/manager."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.exceptions import InvalidModelError, ProviderAPIError
from stratifyai.models import ChatRequest, Message

# ---------------------------------------------------------------------------
# AnthropicProvider – streaming, system-message, vision error, cache cost
# ---------------------------------------------------------------------------


class TestAnthropicProviderExtra:
    """Extended coverage for the Anthropic provider streaming/error paths."""

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_chat_completion_with_system_message(self, mock_cls):
        from stratifyai.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_response = {
            "id": "msg_sys",
            "model": "claude-3-5-sonnet-20241022",
            "content": [{"type": "text", "text": "sys reply"}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 12, "output_tokens": 4},
        }
        mock_client.messages.create = AsyncMock(
            return_value=MagicMock(model_dump=lambda: mock_response)
        )

        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[
                Message(role="system", content="You are helpful."),
                Message(role="user", content="Hi"),
            ],
        )
        resp = await provider.chat_completion(request)
        assert resp.content == "sys reply"
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs.get("system") == "You are helpful."

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_chat_completion_vision_error_raises_provider_error(self, mock_cls):
        from stratifyai.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(
            side_effect=RuntimeError("image not supported for this request")
        )

        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[Message(role="user", content="Tell me about cats")],
        )
        with pytest.raises(ProviderAPIError, match="Vision not supported"):
            await provider.chat_completion(request)

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_chat_completion_generic_error_raises_provider_error(self, mock_cls):
        from stratifyai.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create = AsyncMock(
            side_effect=RuntimeError("network failure")
        )

        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[Message(role="user", content="Hello")],
        )
        with pytest.raises(ProviderAPIError, match="Chat completion failed"):
            await provider.chat_completion(request)

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_chat_completion_stream_yields_chunks(self, mock_cls):
        from stratifyai.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        async def fake_text_stream():
            for token in ["Hello", " world"]:
                yield token

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_stream_ctx.text_stream = fake_text_stream()
        mock_client.messages.stream.return_value = mock_stream_ctx

        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[Message(role="user", content="Hello")],
        )
        chunks = []
        async for chunk in provider.chat_completion_stream(request):
            chunks.append(chunk.content)

        assert chunks == ["Hello", " world"]

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_chat_completion_stream_with_system_message(self, mock_cls):
        from stratifyai.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        async def fake_text_stream():
            yield "response"

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_stream_ctx.text_stream = fake_text_stream()
        mock_client.messages.stream.return_value = mock_stream_ctx

        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[
                Message(role="system", content="Be brief"),
                Message(role="user", content="Hi"),
            ],
        )
        chunks = []
        async for chunk in provider.chat_completion_stream(request):
            chunks.append(chunk.content)
        assert chunks == ["response"]
        call_kwargs = mock_client.messages.stream.call_args.kwargs
        assert call_kwargs.get("system") == "Be brief"

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_chat_completion_stream_vision_error_raises(self, mock_cls):
        from stratifyai.providers.anthropic import AnthropicProvider

        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        mock_stream_ctx = MagicMock()
        mock_stream_ctx.__aenter__ = AsyncMock(
            side_effect=RuntimeError("image invalid for this request")
        )
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_client.messages.stream.return_value = mock_stream_ctx

        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[Message(role="user", content="Hello")],
        )
        with pytest.raises(ProviderAPIError, match="Vision not supported"):
            async for _ in provider.chat_completion_stream(request):
                pass

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    @pytest.mark.asyncio
    async def test_chat_completion_stream_invalid_model(self, mock_cls):
        from stratifyai.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="bad-model",
            messages=[Message(role="user", content="Hi")],
        )
        with pytest.raises(InvalidModelError):
            async for _ in provider.chat_completion_stream(request):
                pass

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    def test_calculate_cache_cost_non_caching_model_returns_zero(self, mock_cls):
        from stratifyai.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key")
        # claude-3-haiku doesn't support caching
        cost = provider._calculate_cache_cost(100, 50, "claude-3-haiku-20240307")
        assert cost == 0.0

    @patch("stratifyai.providers.anthropic.AsyncAnthropic")
    def test_build_sampling_params_top_p_branch(self, mock_cls):
        from stratifyai.providers.anthropic import AnthropicProvider

        provider = AnthropicProvider(api_key="test-key")
        request = ChatRequest(
            model="claude-3-5-sonnet-20241022",
            messages=[Message(role="user", content="hi")],
        )
        # default temperature is 0.7 → top_p branch
        request.top_p = 0.9
        params = provider._build_sampling_params(request)
        assert "top_p" in params


# ---------------------------------------------------------------------------
# BedrockProvider – request builders, normalize_response, stream_chunk paths
# ---------------------------------------------------------------------------


class TestBedrockProviderExtra:
    """Extended coverage for Bedrock request/response helpers."""

    def _make_provider(self):
        from stratifyai.providers.bedrock import BedrockProvider

        with patch("stratifyai.providers.bedrock.aioboto3") as mock_boto:
            mock_boto.Session.return_value = MagicMock()
            provider = BedrockProvider(
                aws_access_key_id="AKIATEST",
                aws_secret_access_key="secret",
                region_name="us-east-1",
            )
        return provider

    def test_build_mistral_request(self):
        provider = self._make_provider()
        request = ChatRequest(
            model="mistral.mistral-large-2402-v1:0",
            messages=[Message(role="user", content="hello")],
        )
        request.top_p = 0.95
        result = provider._build_request_body(request)
        assert "prompt" in result

    def test_build_cohere_request(self):
        provider = self._make_provider()
        request = ChatRequest(
            model="cohere.command-r-plus-v1:0",
            messages=[
                Message(role="user", content="previous message"),
                Message(role="assistant", content="my response"),
                Message(role="user", content="last user message"),
            ],
        )
        result = provider._build_request_body(request)
        assert "message" in result
        assert result["message"] == "last user message"

    def test_normalize_response_for_mistral(self):
        provider = self._make_provider()
        raw = {"outputs": [{"text": "mistral says hi"}]}
        resp = provider._normalize_response(raw, "mistral.mistral-large-2402-v1:0")
        assert resp.content == "mistral says hi"

    def test_normalize_response_for_cohere(self):
        provider = self._make_provider()
        raw = {
            "text": "cohere says hi",
            "prompt_tokens": 6,
            "generation_tokens": 4,
            "finish_reason": "COMPLETE",
        }
        resp = provider._normalize_response(raw, "cohere.command-r-plus-v1:0")
        assert resp.content == "cohere says hi"
        assert resp.usage.prompt_tokens == 6

    def test_normalize_response_for_titan(self):
        provider = self._make_provider()
        raw = {
            "results": [
                {
                    "outputText": "titan output",
                    "completionReason": "FINISH",
                    "inputTextTokenCount": 5,
                    "outputTextTokenCount": 3,
                }
            ]
        }
        resp = provider._normalize_response(raw, "amazon.titan-text-lite-v1")
        assert resp.content == "titan output"

    def test_normalize_response_unknown_model(self):
        provider = self._make_provider()
        raw = {"some": "data"}
        resp = provider._normalize_response(raw, "unknown.model-v1:0")
        assert resp.content == str(raw)

    def test_normalize_stream_chunk_meta_llama(self):
        provider = self._make_provider()
        chunk = {"generation": "llama text"}
        resp = provider._normalize_stream_chunk(
            chunk, "meta.llama3-3-70b-instruct-v1:0"
        )
        assert resp.content == "llama text"

    def test_normalize_stream_chunk_mistral(self):
        provider = self._make_provider()
        chunk = {"outputs": [{"text": "mistral stream"}]}
        resp = provider._normalize_stream_chunk(
            chunk, "mistral.mistral-large-2402-v1:0"
        )
        assert resp.content == "mistral stream"

    def test_normalize_stream_chunk_nova(self):
        provider = self._make_provider()
        chunk = {"contentBlockDelta": {"delta": {"text": "nova stream"}}}
        resp = provider._normalize_stream_chunk(chunk, "amazon.nova-lite-v1:0")
        assert resp.content == "nova stream"

    def test_normalize_stream_chunk_titan(self):
        provider = self._make_provider()
        chunk = {"outputText": "titan stream"}
        resp = provider._normalize_stream_chunk(chunk, "amazon.titan-text-lite-v1")
        assert resp.content == "titan stream"

    def test_normalize_stream_chunk_unknown_model_returns_empty(self):
        provider = self._make_provider()
        chunk = {"some": "data"}
        resp = provider._normalize_stream_chunk(chunk, "unknown.model")
        assert resp.content == ""

    def test_extract_cohere_usage(self):
        provider = self._make_provider()
        usage = provider._extract_cohere_usage(
            {"prompt_tokens": 10, "generation_tokens": 5}, "cohere.command-r-plus-v1:0"
        )
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 5

    def test_messages_to_prompt(self):
        provider = self._make_provider()
        messages = [
            Message(role="system", content="Be brief"),
            Message(role="user", content="Input"),
            Message(role="assistant", content="Sure"),
        ]
        prompt = provider._messages_to_prompt(messages)
        assert "System: Be brief" in prompt
        assert "User: Input" in prompt
        assert "Assistant: Sure" in prompt
        assert prompt.endswith("Assistant:")

    def test_estimate_usage(self):
        provider = self._make_provider()
        usage = provider._estimate_usage(
            "short content", "mistral.mistral-large-2402-v1:0"
        )
        assert usage.completion_tokens == len("short content") // 4


# ---------------------------------------------------------------------------
# mcp_catalog/manager – search/filter, vscode remove, prerequisites warnings
# ---------------------------------------------------------------------------


class TestMCPCatalogManagerExtra:
    """Extended coverage for mcp_catalog/manager utility functions."""

    def test_search_servers_by_query(self):
        from stratifyai.mcp_catalog.manager import list_servers

        results = list_servers(search="postgres")
        assert any(
            "postgres" in s.id.lower() or "postgres" in s.name.lower() for s in results
        )

    def test_search_servers_by_category(self):
        from stratifyai.mcp_catalog.manager import list_servers

        results = list_servers(category="database")
        assert all(s.category == "database" for s in results)

    def test_get_server_raises_for_unknown_id(self):
        from stratifyai.mcp_catalog.manager import get_server

        with pytest.raises(KeyError, match="Unknown MCP server"):
            get_server("not-a-real-server-id-xyz")

    def test_detect_client_config_path_raises_for_unknown_client(self):
        from stratifyai.mcp_catalog.manager import detect_client_config_path

        with pytest.raises(ValueError, match="Unsupported client"):
            detect_client_config_path("unknown-client")

    def test_get_mcp_client_settings_returns_empty_for_nonexistent_path(self, tmp_path):
        from stratifyai.mcp_catalog.manager import get_mcp_client_settings

        _, settings = get_mcp_client_settings(
            "cursor", output_path=str(tmp_path / "missing.json")
        )
        assert settings == {}

    def test_get_mcp_client_settings_reads_existing_metadata(self, tmp_path):
        from stratifyai.mcp_catalog.manager import get_mcp_client_settings

        config_path = tmp_path / "mcp.json"
        config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {"demo": {"command": "python"}},
                    "stratifyai": {
                        "mcpClient": {"servers": {"demo": {"enabled": False}}}
                    },
                }
            ),
            encoding="utf-8",
        )
        _, settings = get_mcp_client_settings("cursor", output_path=str(config_path))
        assert settings["servers"]["demo"]["enabled"] is False

    def test_remove_servers_from_config_vscode_client(self, tmp_path):
        from stratifyai.mcp_catalog.manager import remove_servers_from_config

        config_path = tmp_path / "settings.json"
        config_path.write_text(
            json.dumps({"mcp": {"servers": {"demo": {"command": "python"}}}}),
            encoding="utf-8",
        )
        written_path, removed = remove_servers_from_config(
            "vscode", ["demo"], output_path=str(config_path)
        )
        assert "demo" in removed
        written = json.loads(config_path.read_text(encoding="utf-8"))
        assert "demo" not in written["mcp"]["servers"]

    def test_remove_servers_from_config_empty_targets(self, tmp_path):
        from stratifyai.mcp_catalog.manager import remove_servers_from_config

        config_path = tmp_path / "mcp.json"
        config_path.write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
        _, removed = remove_servers_from_config(
            "cursor", [], output_path=str(config_path)
        )
        assert removed == []

    def test_remove_servers_from_config_missing_file(self, tmp_path):
        from stratifyai.mcp_catalog.manager import remove_servers_from_config

        _, removed = remove_servers_from_config(
            "cursor", ["demo"], output_path=str(tmp_path / "missing.json")
        )
        assert removed == []

    def test_validate_prerequisites_warns_missing_npx(self, monkeypatch):
        import shutil

        from stratifyai.mcp_catalog.manager import validate_prerequisites

        original_which = shutil.which
        monkeypatch.setattr(
            shutil, "which", lambda cmd: None if cmd == "npx" else original_which(cmd)
        )
        warnings = validate_prerequisites(["filesystem"])
        assert any("Node.js" in w or "npx" in w for w in warnings)

    def test_validate_prerequisites_warns_missing_docker(self, monkeypatch):
        import shutil

        from stratifyai.mcp_catalog.manager import (
            list_servers,
            validate_prerequisites,
        )

        # Find a docker-based server
        docker_servers = [s for s in list_servers() if s.install_method == "docker"]
        if not docker_servers:
            pytest.skip("No docker-based MCP servers in catalog")

        original_which = shutil.which
        monkeypatch.setattr(
            shutil,
            "which",
            lambda cmd: None if cmd == "docker" else original_which(cmd),
        )
        warnings = validate_prerequisites([docker_servers[0].id])
        assert any("Docker" in w for w in warnings)

    def test_write_mcp_client_settings_back_up_existing(self, tmp_path):
        from stratifyai.mcp_catalog.manager import write_mcp_client_settings

        config_path = tmp_path / "mcp.json"
        config_path.write_text(
            json.dumps({"mcpServers": {"demo": {"command": "python"}}}),
            encoding="utf-8",
        )
        write_mcp_client_settings(
            "cursor",
            {"servers": {"demo": {"enabled": True}}},
            output_path=str(config_path),
        )
        backup = Path(str(config_path) + ".backup")
        assert backup.exists()
        assert "demo" in json.loads(backup.read_text())["mcpServers"]

    def test_write_mcp_client_settings_raises_for_claude_code(self, tmp_path):
        from stratifyai.mcp_catalog.manager import write_mcp_client_settings

        with pytest.raises(ValueError, match="Claude Code"):
            write_mcp_client_settings(
                "claude-code", {"servers": {}}, project_root=str(tmp_path)
            )

    def test_build_claude_code_commands_with_env_vars(self):
        from stratifyai.mcp_catalog.manager import build_claude_code_commands

        commands = build_claude_code_commands(
            ["filesystem"],
            env_values={},
            arg_values={"filesystem.paths": "/tmp"},
        )
        assert any("filesystem" in cmd for cmd in commands)
