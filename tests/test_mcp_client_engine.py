"""Tests for the MCP client engine core (CE-1)."""

from __future__ import annotations

import json
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from mcp.types import Tool

from stratifyai.mcp_client.config import ConfiguredServer, load_enabled_servers
from stratifyai.mcp_client.engine import MCPClientEngine
from stratifyai.mcp_client.permissions import (
    MCPConfirmationRequiredError,
    PermissionManager,
    PermissionMode,
    ServerPermissionConfig,
)
from stratifyai.mcp_client.server_manager import ServerStatus
from stratifyai.mcp_client.tool_registry import ToolRegistry
from stratifyai.models import ChatResponse, Message, Usage


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
                },
                "stratifyai": {
                    "mcpClient": {
                        "servers": {
                            "demo": {
                                "enabled": False,
                                "auto_start": False,
                                "permissions": {
                                    "allow": ["read_file"],
                                    "confirm": ["delete_*"],
                                },
                            }
                        }
                    }
                },
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
    assert server.enabled is False
    assert server.auto_start is False
    assert server.permissions.allow == ["read_file"]
    assert server.permissions.confirm == ["delete_*"]


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


def test_permission_manager_applies_safety_defaults_and_overrides() -> None:
    manager = PermissionManager(
        {
            "filesystem": ServerPermissionConfig(
                deny=["delete_secret"],
                confirm=["move_*"],
            )
        }
    )
    allow_list_manager = PermissionManager(
        {
            "filesystem": ServerPermissionConfig(
                allow=["write_note"],
            )
        }
    )

    read_tool = Tool(
        name="read_file",
        description="Read a file from disk",
        inputSchema={"type": "object"},
        annotations={"readOnlyHint": True},
    )
    delete_tool = Tool(
        name="delete_file",
        description="Delete a file from disk",
        inputSchema={"type": "object"},
    )

    read_decision = manager.evaluate("filesystem", "read_file", read_tool)
    assert read_decision.mode == PermissionMode.ALLOW

    delete_decision = manager.evaluate("filesystem", "delete_file", delete_tool)
    assert delete_decision.mode == PermissionMode.CONFIRM

    allow_decision = allow_list_manager.evaluate("filesystem", "write_note", None)
    assert allow_decision.mode == PermissionMode.ALLOW
    assert (
        allow_list_manager.evaluate("filesystem", "read_file", read_tool).mode
        == PermissionMode.DENY
    )

    confirm_decision = manager.evaluate("filesystem", "move_file", None)
    assert confirm_decision.mode == PermissionMode.CONFIRM

    deny_decision = manager.evaluate("filesystem", "delete_secret", None)
    assert deny_decision.mode == PermissionMode.DENY


@pytest.mark.asyncio
async def test_mcp_client_engine_blocks_destructive_tools_without_confirmation() -> (
    None
):
    class FakeResult:
        def model_dump(self, mode: str = "json") -> dict[str, object]:
            return {"structuredContent": {"ok": True}}

    class FakeSession:
        def __init__(self) -> None:
            self.call_tool = AsyncMock(return_value=FakeResult())

    engine = MCPClientEngine(
        servers=[ConfiguredServer(server_id="demo", command="python")]
    )
    engine._server_manager._connections["demo"] = type(
        "FakeConnection", (), {"session": FakeSession()}
    )()
    engine._tool_registry.register_server_tools(
        "demo",
        [
            Tool(
                name="read_file",
                description="Read a file",
                inputSchema={"type": "object"},
                annotations={"readOnlyHint": True},
            ),
            Tool(
                name="delete_file",
                description="Delete a file",
                inputSchema={"type": "object"},
                annotations={"destructiveHint": True},
            ),
        ],
    )
    engine._server_manager._statuses["demo"] = ServerStatus(
        server_id="demo", status="connected"
    )

    definitions, _warnings = await engine.build_tool_definitions(
        provider="openai", active_servers=["demo"]
    )

    assert [item["function"]["name"] for item in definitions] == ["demo.read_file"]

    with pytest.raises(MCPConfirmationRequiredError):
        await engine.call_tool("demo", "delete_file", {"path": "/tmp/demo.txt"})


@pytest.mark.asyncio
async def test_mcp_client_engine_confirmation_handler_can_approve_tool() -> None:
    approvals: list[tuple[str, str, dict[str, str]]] = []

    class FakeResult:
        def model_dump(self, mode: str = "json") -> dict[str, object]:
            return {"structuredContent": {"ok": True}}

    class FakeSession:
        def __init__(self) -> None:
            self.call_tool = AsyncMock(return_value=FakeResult())

    def confirm_handler(
        server_id: str,
        tool_name: str,
        arguments: dict[str, str],
        _decision,
    ) -> bool:
        approvals.append((server_id, tool_name, arguments))
        return True

    engine = MCPClientEngine(
        servers=[ConfiguredServer(server_id="demo", command="python")],
        tool_confirmation_handler=confirm_handler,
    )
    engine._server_manager._connections["demo"] = type(
        "FakeConnection", (), {"session": FakeSession()}
    )()
    engine._tool_registry.register_server_tools(
        "demo",
        [
            Tool(
                name="delete_file",
                description="Delete a file",
                inputSchema={"type": "object"},
                annotations={"destructiveHint": True},
            )
        ],
    )
    engine._server_manager._statuses["demo"] = ServerStatus(
        server_id="demo", status="connected"
    )

    result = await engine.call_tool("demo", "delete_file", {"path": "/tmp/demo.txt"})

    assert result["structuredContent"]["ok"] is True
    assert approvals == [("demo", "delete_file", {"path": "/tmp/demo.txt"})]


@pytest.mark.asyncio
async def test_mcp_client_engine_build_tool_definitions_filters_active_servers() -> (
    None
):
    allow_perms = ServerPermissionConfig(default_mode=PermissionMode.ALLOW)
    engine = MCPClientEngine(
        servers=[
            ConfiguredServer(
                server_id="alpha", command="python", permissions=allow_perms
            ),
            ConfiguredServer(
                server_id="beta", command="python", permissions=allow_perms
            ),
        ],
    )
    engine._tool_registry.register_server_tools(
        "alpha",
        [
            Tool(
                name="echo",
                description="Echo alpha",
                inputSchema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                },
            )
        ],
    )
    engine._server_manager._statuses["alpha"] = ServerStatus(
        server_id="alpha", status="connected"
    )
    engine.start_server = AsyncMock(side_effect=RuntimeError("offline"))

    definitions, warnings = await engine.build_tool_definitions(
        provider="openai",
        active_servers=["alpha", "beta", "missing"],
    )

    assert [item["function"]["name"] for item in definitions] == ["alpha.echo"]
    assert any("beta" in warning and "offline" in warning for warning in warnings)
    assert any("missing" in warning for warning in warnings)


@pytest.mark.asyncio
async def test_mcp_client_engine_chat_with_mcp_executes_tool_calls() -> None:
    allow_perms = ServerPermissionConfig(default_mode=PermissionMode.ALLOW)
    engine = MCPClientEngine(
        servers=[
            ConfiguredServer(
                server_id="demo", command="python", permissions=allow_perms
            )
        ],
    )
    engine._tool_registry.register_server_tools(
        "demo",
        [
            Tool(
                name="echo",
                description="Echo tool",
                inputSchema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},
                },
            )
        ],
    )
    engine._server_manager._statuses["demo"] = ServerStatus(
        server_id="demo", status="connected"
    )
    engine.call_tool = AsyncMock(
        return_value={"structuredContent": {"echo": "hello from tool"}}
    )

    first = ChatResponse(
        id="resp-1",
        model="gpt-4.1-mini",
        content="Let me check a tool.",
        finish_reason="tool_calls",
        usage=Usage(prompt_tokens=10, completion_tokens=2, total_tokens=12),
        provider="openai",
        created_at=datetime.now(),
        raw_response={
            "id": "resp-1",
            "model": "gpt-4.1-mini",
            "created": 1,
            "choices": [
                {
                    "message": {
                        "content": "Let me check a tool.",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "demo.echo",
                                    "arguments": '{"text": "hello"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
        },
    )
    second = ChatResponse(
        id="resp-2",
        model="gpt-4.1-mini",
        content="The tool replied with hello from tool.",
        finish_reason="stop",
        usage=Usage(prompt_tokens=20, completion_tokens=6, total_tokens=26),
        provider="openai",
        created_at=datetime.now(),
        raw_response={
            "id": "resp-2",
            "model": "gpt-4.1-mini",
            "created": 2,
            "choices": [
                {
                    "message": {"content": "The tool replied with hello from tool."},
                    "finish_reason": "stop",
                }
            ],
        },
    )

    class FakeLLMClient:
        def __init__(self) -> None:
            self.requests = []
            self.responses = [first, second]

        async def chat_completion(self, request):
            self.requests.append(request)
            return self.responses.pop(0)

    fake_client = FakeLLMClient()
    response = await engine.chat_with_mcp(
        llm_client=fake_client,
        provider="openai",
        model="gpt-4.1-mini",
        messages=[Message(role="user", content="Say hello")],
        active_servers=["demo"],
    )

    assert response.content == "The tool replied with hello from tool."
    assert engine.call_tool.await_count == 1
    assert (
        fake_client.requests[0].extra_params["tools"][0]["function"]["name"]
        == "demo.echo"
    )
    assert "hello from tool" in fake_client.requests[1].messages[-1].content
    assert response.raw_response["mcp_tool_results"][0]["namespace"] == "demo.echo"


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

    allow_perms = ServerPermissionConfig(default_mode=PermissionMode.ALLOW)
    engine = MCPClientEngine(
        servers=[
            ConfiguredServer(
                server_id="demo",
                command=sys.executable,
                args=[str(server_script)],
                cwd=tmp_path,
                permissions=allow_perms,
            )
        ],
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
