"""Tests for MCP tools — uses mocked LLMClient/Router."""

import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from stratifyai.mcp_server import tools as mcp_tools
from stratifyai.mcp_server.server import mcp
from stratifyai.models import ChatResponse, Usage


@pytest.fixture(autouse=True)
def reset_mcp_cost_tracker():
    """Reset the shared MCP cost tracker between tests."""
    mcp_tools._mcp_cost_tracker.reset()
    yield
    mcp_tools._mcp_cost_tracker.reset()


def _get_tool(name: str):
    """Get a registered MCP tool function by name."""
    return mcp._tool_manager._tools[name].fn


class TestListProviders:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        result = await _get_tool("list_providers")()
        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_provider_shape(self):
        result = await _get_tool("list_providers")()
        for item in result:
            assert "provider" in item
            assert "model_count" in item
            assert "configured" in item
            assert isinstance(item["model_count"], int)
            assert isinstance(item["configured"], bool)

    @pytest.mark.asyncio
    async def test_includes_known_providers(self):
        result = await _get_tool("list_providers")()
        names = [p["provider"] for p in result]
        assert "openai" in names
        assert "anthropic" in names


class TestListModels:
    @pytest.mark.asyncio
    async def test_returns_models_for_valid_provider(self):
        result = await _get_tool("list_models")(provider="openai")
        assert isinstance(result, list)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_model_shape(self):
        result = await _get_tool("list_models")(provider="openai")
        for item in result:
            assert "model_id" in item
            assert "context_window" in item
            assert "cost_input_per_1m" in item
            assert "cost_output_per_1m" in item
            assert "capabilities" in item

    @pytest.mark.asyncio
    async def test_invalid_provider_raises_error(self):
        with pytest.raises(ValueError) as exc_info:
            await _get_tool("list_models")(provider="nonexistent")
        payload = json.loads(str(exc_info.value))
        assert payload["error_code"] == "invalid_provider"


class TestGetModelInfo:
    @pytest.mark.asyncio
    async def test_valid_model(self):
        result = await _get_tool("get_model_info")(
            provider="openai", model="gpt-4.1-mini"
        )
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4.1-mini"
        assert "metadata" in result
        assert result["mcp_schema_version"] == 1

    @pytest.mark.asyncio
    async def test_invalid_provider_error(self):
        with pytest.raises(ValueError) as exc_info:
            await _get_tool("get_model_info")(
                provider="nonexistent", model="gpt-4.1-mini"
            )
        payload = json.loads(str(exc_info.value))
        assert payload["error_code"] == "invalid_provider"

    @pytest.mark.asyncio
    async def test_invalid_model_error(self):
        with pytest.raises(ValueError) as exc_info:
            await _get_tool("get_model_info")(
                provider="openai", model="nonexistent-model"
            )
        payload = json.loads(str(exc_info.value))
        assert payload["error_code"] == "invalid_model"


class TestEstimateCost:
    @pytest.mark.asyncio
    async def test_returns_positive_estimate(self):
        result = await _get_tool("estimate_cost")(
            provider="openai",
            model="gpt-4.1-mini",
            message_text="Hello world, this is a test message for cost estimation.",
        )
        assert result["estimated_input_tokens"] > 0
        assert result["estimated_cost_usd"] >= 0
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4.1-mini"
        assert result["mcp_schema_version"] == 1

    @pytest.mark.asyncio
    async def test_invalid_provider_error(self):
        with pytest.raises(ValueError) as exc_info:
            await _get_tool("estimate_cost")(
                provider="fake", model="m", message_text="hi"
            )
        payload = json.loads(str(exc_info.value))
        assert payload["error_code"] == "invalid_provider"

    @pytest.mark.asyncio
    async def test_invalid_model_error(self):
        with pytest.raises(ValueError) as exc_info:
            await _get_tool("estimate_cost")(
                provider="openai", model="fake-model", message_text="hi"
            )
        payload = json.loads(str(exc_info.value))
        assert payload["error_code"] == "invalid_model"


class TestValidateProvider:
    @pytest.mark.asyncio
    async def test_unconfigured_provider(self):
        result = await _get_tool("validate_provider")(provider="openai")
        assert result["provider"] == "openai"
        assert isinstance(result["configured"], bool)
        assert isinstance(result["models_available"], list)
        assert len(result["models_available"]) > 0
        assert result["mcp_schema_version"] == 1

    @pytest.mark.asyncio
    async def test_unknown_provider_shows_no_models(self):
        result = await _get_tool("validate_provider")(provider="nonexistent")
        assert result["models_available"] == []
        assert any("No models found" in e for e in result["validation_errors"])


class TestGetCostSummary:
    @pytest.mark.asyncio
    async def test_fresh_tracker_returns_zeros(self):
        result = await _get_tool("get_cost_summary")()
        assert result["mcp_schema_version"] == 1
        assert isinstance(result["total_cost_usd"], float)
        assert isinstance(result["total_calls"], int)

    @pytest.mark.asyncio
    async def test_summary_updates_after_chat_completion(self, monkeypatch):
        mock_response = ChatResponse(
            id="req-123",
            model="gpt-4.1-mini",
            content="Hello back",
            finish_reason="stop",
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                cost_usd=0.0015,
            ),
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
            latency_ms=12.0,
        )
        mock_client = SimpleNamespace(
            chat_completion=AsyncMock(return_value=mock_response)
        )

        monkeypatch.setattr(mcp_tools, "LLMClient", lambda provider: mock_client)

        await _get_tool("chat_completion")(
            provider="openai",
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": "hello"}],
        )

        summary = await _get_tool("get_cost_summary")()
        assert summary["total_calls"] == 1
        assert summary["total_tokens"] == 15
        assert summary["total_cost_usd"] == pytest.approx(0.0015)
        assert summary["by_provider"]["openai"] == pytest.approx(0.0015)
        assert summary["by_model"]["gpt-4.1-mini"] == pytest.approx(0.0015)

    @pytest.mark.asyncio
    async def test_summary_filters_by_provider_and_model(self):
        mcp_tools._mcp_cost_tracker.add_entry(
            provider="openai",
            model="gpt-4.1-mini",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cost_usd=0.0015,
            request_id="req-1",
        )
        mcp_tools._mcp_cost_tracker.add_entry(
            provider="anthropic",
            model="claude-3-5-haiku-20241022",
            prompt_tokens=20,
            completion_tokens=10,
            total_tokens=30,
            cost_usd=0.003,
            request_id="req-2",
        )

        openai_summary = await _get_tool("get_cost_summary")(provider="openai")
        assert openai_summary["total_calls"] == 1
        assert openai_summary["total_tokens"] == 15
        assert openai_summary["by_provider"] == {"openai": pytest.approx(0.0015)}

        model_summary = await _get_tool("get_cost_summary")(
            model="claude-3-5-haiku-20241022"
        )
        assert model_summary["total_calls"] == 1
        assert model_summary["total_tokens"] == 30
        assert model_summary["by_model"] == {
            "claude-3-5-haiku-20241022": pytest.approx(0.003)
        }


class TestToolValidation:
    @pytest.mark.asyncio
    async def test_chat_completion_rejects_empty_messages(self):
        with pytest.raises(ValueError) as exc_info:
            await _get_tool("chat_completion")(
                provider="openai",
                model="gpt-4o-mini",
                messages=[],
            )

        payload = json.loads(str(exc_info.value))
        assert payload["error_code"] == "validation_error"

    @pytest.mark.asyncio
    async def test_chat_completion_rejects_invalid_temperature_and_max_tokens(self):
        with pytest.raises(ValueError) as exc_info:
            await _get_tool("chat_completion")(
                provider="openai",
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "hello"}],
                temperature=2.5,
                max_tokens=0,
            )

        payload = json.loads(str(exc_info.value))
        assert payload["error_code"] == "validation_error"

    @pytest.mark.asyncio
    async def test_chat_with_routing_rejects_empty_messages(self):
        with pytest.raises(ValueError) as exc_info:
            await _get_tool("chat_with_routing")(messages=[])

        payload = json.loads(str(exc_info.value))
        assert payload["error_code"] == "validation_error"


class TestToolRegistration:
    def test_all_expected_tools_registered(self):
        expected = [
            "chat_completion",
            "chat_with_routing",
            "list_providers",
            "list_models",
            "get_model_info",
            "get_cost_summary",
            "validate_provider",
            "estimate_cost",
        ]
        registered = list(mcp._tool_manager._tools.keys())
        for name in expected:
            assert name in registered, f"Tool '{name}' not registered"
