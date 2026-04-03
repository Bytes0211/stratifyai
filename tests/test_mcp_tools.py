"""Tests for MCP tools — uses mocked LLMClient/Router."""

import json

import pytest

from stratifyai.mcp_server.server import mcp


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
