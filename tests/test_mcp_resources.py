"""Tests for MCP resources."""

import json
from pathlib import Path

import pytest

from stratifyai.mcp_server import tools as mcp_tools
from stratifyai.mcp_server.server import mcp


@pytest.fixture(autouse=True)
def reset_mcp_cost_tracker():
    """Reset the shared MCP cost tracker between tests."""
    mcp_tools._mcp_cost_tracker.reset()
    yield
    mcp_tools._mcp_cost_tracker.reset()


def _get_resource(uri: str):
    """Get a registered MCP resource function by URI."""
    if uri in mcp._resource_manager._resources:
        return mcp._resource_manager._resources[uri].fn
    if uri in mcp._resource_manager._templates:
        return mcp._resource_manager._templates[uri].fn
    raise KeyError(f"Resource '{uri}' not found")


class TestCatalogResource:
    @pytest.mark.asyncio
    async def test_returns_valid_json(self):
        fn = _get_resource("stratifyai://catalog")
        result = await fn()
        data = json.loads(result)
        assert "providers" in data
        assert "version" in data
        assert "updated" in data

    @pytest.mark.asyncio
    async def test_contains_known_providers(self):
        fn = _get_resource("stratifyai://catalog")
        result = await fn()
        data = json.loads(result)
        providers = data["providers"]
        assert "openai" in providers
        assert "anthropic" in providers

    @pytest.mark.asyncio
    async def test_matches_expected_top_level_schema_shape(self):
        fn = _get_resource("stratifyai://catalog")
        result = await fn()
        data = json.loads(result)

        schema_path = Path(__file__).resolve().parent.parent / "catalog" / "schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        assert data.keys() >= set(schema["required"])
        assert isinstance(data["providers"], dict)


class TestCatalogProviderResource:
    @pytest.mark.asyncio
    async def test_valid_provider(self):
        fn = _get_resource("stratifyai://catalog/{provider}")
        result = await fn(provider="openai")
        data = json.loads(result)
        assert isinstance(data, dict)
        assert len(data) > 0

    @pytest.mark.asyncio
    async def test_returns_only_requested_provider_models(self):
        fn = _get_resource("stratifyai://catalog/{provider}")
        result = await fn(provider="openai")
        data = json.loads(result)

        assert "gpt-4.1-mini" in data
        assert not any(model_id.startswith("claude") for model_id in data)

    @pytest.mark.asyncio
    async def test_invalid_provider_raises(self):
        fn = _get_resource("stratifyai://catalog/{provider}")
        with pytest.raises(ValueError, match="Unknown provider"):
            await fn(provider="nonexistent")


class TestProvidersResource:
    @pytest.mark.asyncio
    async def test_returns_provider_list(self):
        fn = _get_resource("stratifyai://providers")
        result = await fn()
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) > 0
        for item in data:
            assert "provider" in item
            assert "model_count" in item
            assert "configured" in item


class TestCostsResource:
    @pytest.mark.asyncio
    async def test_returns_json(self):
        fn = _get_resource("stratifyai://costs")
        result = await fn()
        data = json.loads(result)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_returns_mcp_cost_summary_shape(self):
        mcp_tools._mcp_cost_tracker.add_entry(
            provider="openai",
            model="gpt-4.1-mini",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cost_usd=0.0015,
            request_id="req-1",
        )

        fn = _get_resource("stratifyai://costs")
        result = await fn()
        data = json.loads(result)

        assert data["mcp_schema_version"] == 1
        assert data["total_cost_usd"] == pytest.approx(0.0015)
        assert data["total_calls"] == 1
        assert data["total_tokens"] == 15
        assert data["by_provider"] == {"openai": pytest.approx(0.0015)}
        assert data["by_model"] == {"gpt-4.1-mini": pytest.approx(0.0015)}


class TestRouterStrategiesResource:
    @pytest.mark.asyncio
    async def test_returns_four_strategies(self):
        fn = _get_resource("stratifyai://router/strategies")
        result = await fn()
        data = json.loads(result)
        assert len(data) == 4
        names = [s["name"] for s in data]
        assert "cost" in names
        assert "quality" in names
        assert "latency" in names
        assert "hybrid" in names

    @pytest.mark.asyncio
    async def test_strategy_shape(self):
        fn = _get_resource("stratifyai://router/strategies")
        result = await fn()
        data = json.loads(result)
        for strategy in data:
            assert "name" in strategy
            assert "description" in strategy
            assert isinstance(strategy["description"], str)


class TestResourceRegistration:
    def test_static_resources_registered(self):
        expected = [
            "stratifyai://catalog",
            "stratifyai://providers",
            "stratifyai://costs",
            "stratifyai://router/strategies",
        ]
        for uri in expected:
            assert uri in mcp._resource_manager._resources, (
                f"Resource '{uri}' not registered"
            )

    def test_template_resource_registered(self):
        assert "stratifyai://catalog/{provider}" in mcp._resource_manager._templates
