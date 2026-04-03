"""MCP server initialization — composes tools, resources, and prompts."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from stratifyai.mcp_server import prompts, resources, tools

mcp = FastMCP("stratifyai")

tools.register(mcp)
resources.register(mcp)
prompts.register(mcp)
