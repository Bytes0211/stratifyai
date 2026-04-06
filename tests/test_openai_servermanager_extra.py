"""Extended tests for OpenAI provider branches and MCP server manager lifecycle."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# OpenAI provider — cover missed branches
# ---------------------------------------------------------------------------
class TestOpenAIProviderExtra:
    """Extra coverage for providers/openai.py uncovered branches."""

    def _make_provider(self):
        """Create an OpenAIProvider with a mocked AsyncOpenAI client."""
        with patch("stratifyai.providers.openai.AsyncOpenAI"):
            from stratifyai.providers.openai import OpenAIProvider

            p = OpenAIProvider(api_key="test-key")
            p._client = MagicMock()
            return p

    def _minimal_raw_response(
        self, content="Hello", model="gpt-4o", finish_reason="stop"
    ):
        """Build a minimal raw response dict matching OpenAI format."""
        return {
            "id": "chatcmpl-1",
            "object": "chat.completion",
            "created": 1700000000,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": finish_reason,
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
                "prompt_tokens_details": {"cached_tokens": 0},
                "completion_tokens_details": {"reasoning_tokens": 0},
            },
        }

    def test_get_supported_models(self):
        p = self._make_provider()
        models = p.get_supported_models()
        assert len(models) > 0

    def test_supports_caching_known_model(self):
        p = self._make_provider()
        # gpt-4o supports caching per catalog
        result = p.supports_caching("gpt-4o")
        assert isinstance(result, bool)

    def test_is_reasoning_model_o1(self):
        p = self._make_provider()
        assert p._is_reasoning_model("o1-mini") is True

    def test_is_reasoning_model_o3(self):
        p = self._make_provider()
        assert p._is_reasoning_model("o3-mini") is True

    def test_is_reasoning_model_normal(self):
        p = self._make_provider()
        assert p._is_reasoning_model("gpt-4o") is False

    def test_normalize_response_valid(self):
        p = self._make_provider()
        raw = self._minimal_raw_response()
        resp = p._normalize_response(raw)
        assert resp.content == "Hello"
        assert resp.provider == "openai"

    def test_normalize_response_missing_choices_raises(self):
        from stratifyai.exceptions import ProviderAPIError

        p = self._make_provider()
        with pytest.raises(ProviderAPIError, match="choices"):
            p._normalize_response(
                {"id": "x", "model": "gpt-4o", "created": 0, "choices": []}
            )

    def test_normalize_response_missing_message_raises(self):
        from stratifyai.exceptions import ProviderAPIError

        p = self._make_provider()
        raw = {
            "id": "x",
            "model": "gpt-4o",
            "created": 0,
            "choices": [
                {"index": 0, "message": {"role": "assistant"}, "finish_reason": "stop"}
            ],
            "usage": {},
        }
        with pytest.raises(ProviderAPIError, match="message content"):
            p._normalize_response(raw)

    def test_normalize_response_with_cache_tokens(self):
        p = self._make_provider()
        raw = self._minimal_raw_response()
        raw["usage"]["prompt_tokens_details"] = {
            "cached_tokens": 500,
            "cache_creation_input_tokens": 100,
        }
        raw["usage"]["completion_tokens_details"] = {"reasoning_tokens": 0}
        resp = p._normalize_response(raw)
        assert resp.usage.cached_tokens == 500

    def test_normalize_stream_chunk_valid(self):
        p = self._make_provider()
        chunk = {
            "id": "chunk1",
            "model": "gpt-4o",
            "created": 1700000000,
            "choices": [
                {"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}
            ],
        }
        resp = p._normalize_stream_chunk(chunk)
        assert resp.content == "Hello"

    def test_normalize_stream_chunk_empty_choices_raises(self):
        from stratifyai.exceptions import ProviderAPIError

        p = self._make_provider()
        with pytest.raises(ProviderAPIError, match="choices"):
            p._normalize_stream_chunk(
                {"id": "x", "model": "gpt-4o", "created": 0, "choices": []}
            )

    def test_normalize_stream_chunk_invalid_delta_raises(self):
        from stratifyai.exceptions import ProviderAPIError

        p = self._make_provider()
        chunk = {
            "id": "x",
            "model": "gpt-4o",
            "created": 0,
            "choices": [{"index": 0, "delta": None, "finish_reason": None}],
        }
        with pytest.raises(ProviderAPIError, match="delta"):
            p._normalize_stream_chunk(chunk)

    @pytest.mark.asyncio
    async def test_chat_completion_invalid_model(self):
        from stratifyai.exceptions import InvalidModelError
        from stratifyai.models import ChatRequest, Message

        p = self._make_provider()
        request = ChatRequest(
            model="not-a-real-model-xyz",
            messages=[Message(role="user", content="Hello")],
        )
        with pytest.raises(InvalidModelError):
            await p.chat_completion(request)

    @pytest.mark.asyncio
    async def test_chat_completion_vision_error_raises_provider_error(self):
        """Vision error message should be wrapped in ProviderAPIError."""
        from stratifyai.exceptions import ProviderAPIError
        from stratifyai.models import ChatRequest, Message

        p = self._make_provider()
        # Use a real model to pass validation
        p.validate_model = MagicMock(return_value=True)
        p._client.chat = MagicMock()
        p._client.chat.completions = MagicMock()
        p._client.chat.completions.create = AsyncMock(
            side_effect=Exception("image_url is only supported by certain models")
        )
        request = ChatRequest(
            model="gpt-4o",
            messages=[Message(role="user", content="Hello")],
        )
        with pytest.raises(ProviderAPIError):
            await p.chat_completion(request)

    @pytest.mark.asyncio
    async def test_chat_completion_generic_error_raises_provider_error(self):
        from stratifyai.exceptions import ProviderAPIError
        from stratifyai.models import ChatRequest, Message

        p = self._make_provider()
        p.validate_model = MagicMock(return_value=True)
        p._client.chat = MagicMock()
        p._client.chat.completions = MagicMock()
        p._client.chat.completions.create = AsyncMock(
            side_effect=Exception("connection error")
        )
        request = ChatRequest(
            model="gpt-4o",
            messages=[Message(role="user", content="Hello")],
        )
        with pytest.raises(ProviderAPIError, match="connection error"):
            await p.chat_completion(request)

    @pytest.mark.asyncio
    async def test_chat_completion_reasoning_model_skips_temperature(self):
        """o1/o3 models should not have temperature in params."""
        from stratifyai.models import ChatRequest, Message

        p = self._make_provider()
        p.validate_model = MagicMock(return_value=True)

        captured_params = {}

        async def fake_create(**kwargs):
            captured_params.update(kwargs)
            resp = MagicMock()
            resp.model_dump = MagicMock(
                return_value=self._minimal_raw_response(model="o1-mini")
            )
            return resp

        p._client.chat = MagicMock()
        p._client.chat.completions = MagicMock()
        p._client.chat.completions.create = fake_create

        request = ChatRequest(
            model="o1-mini",
            messages=[Message(role="user", content="Hi")],
        )
        await p.chat_completion(request)
        assert "temperature" not in captured_params

    @pytest.mark.asyncio
    async def test_chat_completion_stream_invalid_model_raises(self):
        from stratifyai.exceptions import InvalidModelError
        from stratifyai.models import ChatRequest, Message

        p = self._make_provider()
        request = ChatRequest(
            model="not-a-real-model-xyz",
            messages=[Message(role="user", content="Hello")],
        )
        with pytest.raises(InvalidModelError):
            async for _ in p.chat_completion_stream(request):
                pass

    @pytest.mark.asyncio
    async def test_chat_completion_stream_api_error_wrapped(self):
        from stratifyai.exceptions import ProviderAPIError
        from stratifyai.models import ChatRequest, Message

        p = self._make_provider()
        p.validate_model = MagicMock(return_value=True)
        p._client.chat = MagicMock()
        p._client.chat.completions = MagicMock()
        p._client.chat.completions.create = AsyncMock(
            side_effect=Exception("network timeout")
        )
        request = ChatRequest(
            model="gpt-4o",
            messages=[Message(role="user", content="Hello")],
        )
        with pytest.raises(ProviderAPIError, match="Streaming"):
            async for _ in p.chat_completion_stream(request):
                pass

    @pytest.mark.asyncio
    async def test_chat_completion_stream_vision_error_wrapped(self):
        from stratifyai.exceptions import ProviderAPIError
        from stratifyai.models import ChatRequest, Message

        p = self._make_provider()
        p.validate_model = MagicMock(return_value=True)
        p._client.chat = MagicMock()
        p._client.chat.completions = MagicMock()
        p._client.chat.completions.create = AsyncMock(
            side_effect=Exception("image_url is only supported by certain models")
        )
        request = ChatRequest(
            model="gpt-4o",
            messages=[Message(role="user", content="Hello")],
        )
        with pytest.raises(ProviderAPIError, match="Vision not supported"):
            async for _ in p.chat_completion_stream(request):
                pass


# ---------------------------------------------------------------------------
# mcp_client/server_manager.py  — cover spawn/stop/restart/check_health/restart
# ---------------------------------------------------------------------------
class TestServerManagerExtra:
    """Cover stratifyai/mcp_client/server_manager.py."""

    def _make_manager(self):
        from stratifyai.mcp_client.server_manager import ServerManager

        return ServerManager()

    def _make_config(self, server_id="test-server"):
        from stratifyai.mcp_client.config import ConfiguredServer

        return ConfiguredServer(
            server_id=server_id,
            command="echo",
            args=["hello"],
            env={},
        )

    @pytest.mark.asyncio
    async def test_spawn_new_server_stores_connection(self):
        mgr = self._make_manager()
        config = self._make_config()

        mock_conn = MagicMock()
        mock_conn.connect = AsyncMock()

        with patch(
            "stratifyai.mcp_client.server_manager.MCPServerConnection",
            return_value=mock_conn,
        ):
            conn = await mgr.spawn(config)

        assert conn is mock_conn
        assert "test-server" in mgr._connections

    @pytest.mark.asyncio
    async def test_spawn_returns_existing_connection(self):
        """Calling spawn twice should return the cached connection."""
        mgr = self._make_manager()
        config = self._make_config()

        mock_conn = MagicMock()
        mock_conn.connect = AsyncMock()
        mgr._connections[config.server_id] = mock_conn

        conn = await mgr.spawn(config)
        assert conn is mock_conn

    @pytest.mark.asyncio
    async def test_spawn_connection_error_marks_status_error(self):
        mgr = self._make_manager()
        config = self._make_config()

        mock_conn = MagicMock()
        mock_conn.connect = AsyncMock(side_effect=Exception("connect failed"))
        mock_conn.close = AsyncMock()

        with patch(
            "stratifyai.mcp_client.server_manager.MCPServerConnection",
            return_value=mock_conn,
        ):
            with pytest.raises(Exception, match="connect failed"):
                await mgr.spawn(config)

        assert mgr._statuses["test-server"].status == "error"

    @pytest.mark.asyncio
    async def test_stop_existing_connection(self):
        mgr = self._make_manager()
        mock_conn = MagicMock()
        mock_conn.close = AsyncMock()
        mgr._connections["s1"] = mock_conn

        await mgr.stop("s1")

        assert "s1" not in mgr._connections
        assert mgr._statuses["s1"].status == "stopped"

    @pytest.mark.asyncio
    async def test_stop_nonexistent_server(self):
        mgr = self._make_manager()
        await mgr.stop("not-there")
        assert mgr._statuses["not-there"].status == "stopped"

    @pytest.mark.asyncio
    async def test_restart_stops_and_respawns(self):
        mgr = self._make_manager()
        config = self._make_config("srv1")

        mock_conn = MagicMock()
        mock_conn.connect = AsyncMock()
        mock_conn.close = AsyncMock()
        mgr._connections["srv1"] = mock_conn

        new_conn = MagicMock()
        new_conn.connect = AsyncMock()
        new_conn.close = AsyncMock()

        with patch(
            "stratifyai.mcp_client.server_manager.MCPServerConnection",
            return_value=new_conn,
        ):
            result = await mgr.restart(config)

        assert result is new_conn

    @pytest.mark.asyncio
    async def test_check_health_no_connection(self):
        mgr = self._make_manager()
        status = await mgr.check_health("unknown-server")
        assert status.status in ("stopped", "error", "unknown", "connected")

    @pytest.mark.asyncio
    async def test_check_health_connected_updates_latency(self):
        mgr = self._make_manager()
        mock_conn = MagicMock()
        mock_conn.probe = AsyncMock(return_value=12.5)
        mgr._connections["srv1"] = mock_conn
        from stratifyai.mcp_client.server_manager import ServerStatus

        mgr._statuses["srv1"] = ServerStatus(server_id="srv1", status="connected")

        status = await mgr.check_health("srv1")
        assert status.latency_ms == 12.5
        assert status.status == "connected"

    @pytest.mark.asyncio
    async def test_check_health_probe_error_marks_error(self):
        mgr = self._make_manager()
        mock_conn = MagicMock()
        mock_conn.probe = AsyncMock(side_effect=Exception("probe fail"))
        mock_conn.close = AsyncMock()
        mgr._connections["srv1"] = mock_conn
        from stratifyai.mcp_client.server_manager import ServerStatus

        mgr._statuses["srv1"] = ServerStatus(server_id="srv1", status="connected")

        status = await mgr.check_health("srv1")
        assert status.status == "error"
        assert "srv1" not in mgr._connections

    def test_get_connection_existing(self):
        mgr = self._make_manager()
        mock_conn = MagicMock()
        mgr._connections["s1"] = mock_conn
        assert mgr.get_connection("s1") is mock_conn

    def test_get_connection_missing(self):
        mgr = self._make_manager()
        assert mgr.get_connection("missing") is None
