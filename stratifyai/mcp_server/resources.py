"""MCP resource registrations — expose catalog and config context."""

from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from stratifyai.api_key_helper import APIKeyHelper
from stratifyai.catalog_manager import load_catalog
from stratifyai.config import MODEL_CATALOG
from stratifyai.router import RoutingStrategy


def register(mcp: FastMCP) -> None:
    """Register all MCP resources on the server instance."""

    @mcp.resource("stratifyai://catalog")
    async def catalog_resource() -> str:
        """Full model catalog as JSON."""
        catalog = load_catalog()
        return json.dumps(catalog, indent=2)

    @mcp.resource("stratifyai://catalog/{provider}")
    async def catalog_provider_resource(provider: str) -> str:
        """Model catalog for a single provider."""
        data = MODEL_CATALOG.get(provider)
        if data is None:
            raise ValueError(f"Unknown provider: {provider}")
        return json.dumps(data, indent=2)

    @mcp.resource("stratifyai://providers")
    async def providers_resource() -> str:
        """List of providers with configuration status."""
        catalog = load_catalog()
        providers = catalog.get("providers", {})
        result: list[dict[str, Any]] = []
        for name, models in providers.items():
            env_key = APIKeyHelper.PROVIDER_ENV_KEYS.get(name)
            result.append(
                {
                    "provider": name,
                    "model_count": len(models),
                    "configured": bool(os.environ.get(env_key)) if env_key else False,
                }
            )
        return json.dumps(result, indent=2)

    @mcp.resource("stratifyai://costs")
    async def costs_resource() -> str:
        """Current session cost summary."""
        from stratifyai.mcp_server.tools import _mcp_cost_tracker

        summary = _mcp_cost_tracker.get_summary()
        return json.dumps(summary, indent=2)

    @mcp.resource("stratifyai://router/strategies")
    async def router_strategies_resource() -> str:
        """Available routing strategies."""
        strategies = [
            {
                "name": s.value,
                "description": {
                    "cost": "Optimize for lowest cost per token",
                    "quality": "Optimize for highest quality output",
                    "latency": "Optimize for fastest response time",
                    "hybrid": "Balanced optimization across cost, quality, and latency",
                }.get(s.value, s.value),
            }
            for s in RoutingStrategy
        ]
        return json.dumps(strategies, indent=2)
