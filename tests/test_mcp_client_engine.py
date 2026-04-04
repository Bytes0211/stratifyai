"""Tests for the MCP client engine core (CE-1)."""

from __future__ import annotations

import json
import sys
import textwrap
from pathlib import Path

import pytest
from mcp.types import Tool

from stratifyai.mcp_client.config import ConfiguredServer, load_enabled_servers
from stratifyai.mcp_client.engine import MCPClientEngine
from stratifyai.mcp_client.tool_registry import ToolRegistry


def test_load_enabled_servers_from_cursor_config(tmp_path: Path) -> None:
    config_path = tmp_path / ".cursor" / "mcp.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "demo": {
                        "command": "python",
                        "args": ["-m", "demo.server"],
                        "env": {"DEMO_TOKEN": "secret"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    servers = load_enabled_servers(client="cursor", project_root=tmp_path)

    assert len(servers) == 1
    server = servers[0]
    assert server.server_id == "demo"
    assert server.command == "python"
    assert server.args == ["-m", "demo.server"]
    assert server.env["DEMO_TOKEN"] == "secret"
    assert server.enabled is True
    assert server.auto_start is True


def test_tool_registry_namespaces_server_tools() -> None:
    registry = ToolRegistry()
    registry.register_server_tools(
        "demo",
        [
            Tool(
                name="echo",
                description="Echo tool",
                inputSchema={"type": "object"},
            )
        ],
    )

    tools = registry.list_all()
    assert len(tools) == 1
    assert tools[0].namespace == "demo.echo"
    assert tools[0].server_id == "demo"
    assert registry.find_tool("demo", "echo") is not None

    registry.unregister_server("demo")
    assert registry.list_all() == []


def test_tool_registry_handles_multiple_servers_and_namespace_lookup() -> None:
    registry = ToolRegistry()
    registry.register_server_tools(
        "alpha",
        [
            Tool(
                name="echo",
                description="Echo alpha",
                inputSchema={"type": "object"},
            )
        ],
    )
    registry.register_server_tools(
        "beta",
        [
            Tool(
                name="echo",
                description="Echo beta",
                inputSchema={"type": "object"},
            ),
            Tool(
                name="sum",
                description="Sum values",
                inputSchema={"type": "object"},
            ),
        ],
    )

    namespaces = [tool.namespace for tool in registry.list_all()]
    assert namespaces == ["alpha.echo", "beta.echo", "beta.sum"]
    assert registry.find_tool("beta", "sum") is not None
    assert registry.find_by_namespace("beta.echo") is not None
    assert registry.list_server_tools("beta")[1].namespace == "beta.sum"

    registry.unregister_server("alpha")
    namespaces = [tool.namespace for tool in registry.list_all()]
    assert namespaces == ["beta.echo", "beta.sum"]


@pytest.mark.asyncio
async def test_mcp_client_engine_start_call_tool_and_get_resource(
    tmp_path: Path,
) -> None:
    server_script = tmp_path / "fake_mcp_server.py"
    server_script.write_text(
        textwrap.dedent(
            """
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("demo-test")

            @mcp.tool()
            async def echo(text: str) -> dict[str, str]:
                return {"echo": text}

            @mcp.resource("demo://status")
            async def status() -> str:
                return "ready"

            if __name__ == "__main__":
                mcp.run(transport="stdio")
            """
        ),
        encoding="utf-8",
    )

    engine = MCPClientEngine(
        servers=[
            ConfiguredServer(
                server_id="demo",
                command=sys.executable,
                args=[str(server_script)],
                cwd=tmp_path,
            )
        ]
    )

    try:
        await engine.start()

        statuses = engine.list_servers()
        assert len(statuses) == 1
        assert statuses[0].server_id == "demo"
        assert statuses[0].status == "connected"

        tools = engine.list_tools()
        assert any(tool.namespace == "demo.echo" for tool in tools)

        result = await engine.call_tool("demo", "echo", {"text": "hello"})
        assert result["structuredContent"]["echo"] == "hello"

        resource = await engine.get_resource("demo", "demo://status")
        assert "ready" in resource
    finally:
        await engine.stop()


@pytest.mark.asyncio
async def test_mcp_client_engine_start_stop_and_restart_updates_registry(
    tmp_path: Path,
) -> None:
    server_script = tmp_path / "fake_mcp_server_reconnect.py"
    server_script.write_text(
        textwrap.dedent(
            """
            from mcp.server.fastmcp import FastMCP

            mcp = FastMCP("demo-reconnect")

            @mcp.tool()
            async def echo(text: str) -> dict[str, str]:
                return {"echo": text}

            if __name__ == "__main__":
                mcp.run(transport="stdio")
            """
        ),
        encoding="utf-8",
    )

    server = ConfiguredServer(
        server_id="demo",
        command=sys.executable,
        args=[str(server_script)],
        cwd=tmp_path,
    )
    engine = MCPClientEngine(servers=[server])

    try:
        await engine.start_server("demo")
        assert [tool.namespace for tool in engine.list_tools()] == ["demo.echo"]
        assert engine.find_tool("demo", "echo") is not None
        assert engine.get_server_status("demo").status == "connected"

        await engine.stop_server("demo")
        assert engine.list_tools() == []
        assert engine.get_server_status("demo").status == "stopped"

        await engine.restart_server("demo")
        assert [tool.namespace for tool in engine.list_tools()] == ["demo.echo"]
        assert engine.get_server_status("demo").status == "connected"
    finally:
        await engine.stop()
