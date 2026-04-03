"""StratifyAI MCP Server — Model Context Protocol interface."""

from __future__ import annotations


def create_server():
    """Create and return the MCP server instance."""
    from stratifyai.mcp_server.server import mcp

    return mcp
