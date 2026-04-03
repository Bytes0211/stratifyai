"""Tests for MCP resources."""

import json

import pytest

from stratifyai.mcp_server.server import mcp


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

    @pytest.mark.asyncio
    async def test_contains_known_providers(self):
        fn = _get_resource("stratifyai://catalog")
        result = await fn()
        data = json.loads(result)
        providers = data["providers"]
        assert "openai" in providers
        assert "anthropic" in providers


class TestCatalogProviderResource:
    @pytest.mark.asyncio
    async def test_valid_provider(self):
        fn = _get_resource("stratifyai://catalog/{provider}")
        result = await fn(provider="openai")
        data = json.loads(result)
        assert isinstance(data, dict)
        assert len(data) > 0

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
