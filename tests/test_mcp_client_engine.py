"""Tests for the MCP client engine core (CE-1)."""

from __future__ import annotations

import json
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import Tool

from stratifyai.mcp_catalog.manager import build_client_config
from stratifyai.mcp_client.config import ConfiguredServer, load_enabled_servers
from stratifyai.mcp_client.connection import _resolve_command_path
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


def test_load_enabled_servers_auto_merges_supported_client_configs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cursor_path = tmp_path / ".cursor" / "mcp.json"
    cursor_path.parent.mkdir(parents=True, exist_ok=True)
    cursor_path.write_text(
        json.dumps(
            {"mcpServers": {"postgresql": {"command": "uvx", "args": ["pg-mcp"]}}}
        ),
        encoding="utf-8",
    )

    claude_path = tmp_path / "claude_desktop_config.json"
    claude_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "postgresql": {"command": "uvx", "args": ["pg-mcp"]},
                    "brave-search": {"command": "npx", "args": ["-y", "brave-mcp"]},
                }
            }
        ),
        encoding="utf-8",
    )

    from stratifyai.mcp_catalog import manager as catalog_manager

    original_detect = catalog_manager.detect_client_config_path

    def fake_detect(client: str, project_root: str | Path | None = None):
        if client == "claude-desktop":
            return claude_path
        return original_detect(client, project_root=project_root)

    monkeypatch.setattr(catalog_manager, "detect_client_config_path", fake_detect)

    servers = load_enabled_servers(client="auto", project_root=tmp_path)

    assert [server.server_id for server in servers] == ["postgresql", "brave-search"]
    assert servers[0].source_client == "claude-desktop"


def test_build_client_config_defaults_filesystem_paths_to_project_root(
    tmp_path: Path,
) -> None:
    config = build_client_config(
        client="cursor",
        server_ids=["filesystem"],
        project_root=tmp_path,
    )

    filesystem = config["mcpServers"]["filesystem"]
    assert str(tmp_path) in filesystem["args"]
    assert "<paths>" not in " ".join(filesystem["args"])
    assert "/home/user/projects" not in " ".join(filesystem["args"])


def test_resolve_command_path_prefers_windows_npx_launcher(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("os.name", "nt")

    def fake_which(command: str) -> str | None:
        mapping = {
            "npx": None,
            "npx.cmd": r"C:\\Program Files\\nodejs\\npx.cmd",
            "npx.exe": None,
        }
        return mapping.get(command)

    monkeypatch.setattr("shutil.which", fake_which)

    assert _resolve_command_path("npx") == r"C:\\Program Files\\nodejs\\npx.cmd"


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
    query_tool = Tool(
        name="query",
        description="Run a read-only SQL query",
        inputSchema={"type": "object"},
    )

    read_decision = manager.evaluate("filesystem", "read_file", read_tool)
    assert read_decision.mode == PermissionMode.ALLOW

    query_decision = manager.evaluate("postgresql", "query", query_tool)
    assert query_decision.mode == PermissionMode.ALLOW

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

    assert [item["function"]["name"] for item in definitions] == ["mcp_demo__read_file"]

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

    assert [item["function"]["name"] for item in definitions] == ["mcp_alpha__echo"]
    assert any("beta" in warning and "offline" in warning for warning in warnings)
    assert any("missing" in warning for warning in warnings)


@pytest.mark.asyncio
async def test_mcp_client_engine_formats_anthropic_tools_with_safe_names() -> None:
    allow_perms = ServerPermissionConfig(default_mode=PermissionMode.ALLOW)
    engine = MCPClientEngine(
        servers=[
            ConfiguredServer(
                server_id="brave-search", command="python", permissions=allow_perms
            )
        ],
    )
    engine._tool_registry.register_server_tools(
        "brave-search",
        [
            Tool(
                name="brave_web_search",
                description="Search the web",
                inputSchema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
            )
        ],
    )
    engine._server_manager._statuses["brave-search"] = ServerStatus(
        server_id="brave-search", status="connected"
    )

    definitions, warnings = await engine.build_tool_definitions(
        provider="anthropic",
        active_servers=["brave-search"],
    )

    assert warnings == []
    assert definitions == [
        {
            "name": "mcp_brave-search__brave_web_search",
            "description": "Search the web",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
        }
    ]
    assert engine._resolve_tool_target(
        "mcp_brave-search__brave_web_search",
        {"brave-search"},
    ) == ("brave-search", "brave_web_search")


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
        == "mcp_demo__echo"
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
async def test_mcp_client_engine_start_continues_when_one_server_fails() -> None:
    engine = MCPClientEngine(
        servers=[
            ConfiguredServer(server_id="broken", command="python"),
            ConfiguredServer(server_id="demo", command="python"),
        ]
    )

    async def fake_start_server(server_id: str):
        if server_id == "broken":
            raise RuntimeError("boom")
        engine._server_manager._statuses[server_id] = ServerStatus(
            server_id=server_id,
            status="connected",
        )
        return engine._server_manager._statuses[server_id]

    engine.start_server = AsyncMock(side_effect=fake_start_server)  # type: ignore[method-assign]

    await engine.start()

    statuses = {status.server_id: status.status for status in engine.list_servers()}
    assert statuses["broken"] == "stopped"
    assert statuses["demo"] == "connected"
    assert engine.start_server.await_count == 2

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


@pytest.mark.asyncio
async def test_mcp_client_engine_sync_configured_servers_restarts_and_removes() -> None:
    allow_perms = ServerPermissionConfig(default_mode=PermissionMode.ALLOW)
    engine = MCPClientEngine(
        servers=[
            ConfiguredServer(
                server_id="keep",
                command="python",
                args=["old"],
                permissions=allow_perms,
            ),
            ConfiguredServer(server_id="remove", command="python"),
            ConfiguredServer(server_id="disable", command="python"),
        ]
    )

    engine._server_manager._connections = {
        "keep": MagicMock(),
        "remove": MagicMock(),
        "disable": MagicMock(),
    }
    engine.stop_server = AsyncMock()  # type: ignore[method-assign]
    engine.restart_server = AsyncMock()  # type: ignore[method-assign]

    desired_servers = [
        ConfiguredServer(
            server_id="keep",
            command="python",
            args=["new"],
            permissions=allow_perms,
            source_client="cursor",
        ),
        ConfiguredServer(
            server_id="disable",
            command="python",
            enabled=False,
            permissions=allow_perms,
        ),
        ConfiguredServer(
            server_id="new",
            command="uvx",
            args=["demo"],
            permissions=allow_perms,
        ),
    ]

    with patch(
        "stratifyai.mcp_client.engine.load_enabled_servers",
        return_value=desired_servers,
    ):
        await engine.sync_configured_servers(client="auto")

    assert [server.server_id for server in engine._servers] == [
        "keep",
        "disable",
        "new",
    ]
    assert engine._server_index["keep"].args == ["new"]
    assert engine._server_index["keep"].source_client == "cursor"
    assert "remove" not in engine._server_index
    engine.restart_server.assert_awaited_once_with("keep")
    engine.stop_server.assert_any_await("remove")
    engine.stop_server.assert_any_await("disable")


@pytest.mark.asyncio
async def test_mcp_client_engine_execute_tool_requests_reports_unknown_and_failures() -> (
    None
):
    allow_perms = ServerPermissionConfig(default_mode=PermissionMode.ALLOW)
    engine = MCPClientEngine(
        servers=[
            ConfiguredServer(
                server_id="alpha", command="python", permissions=allow_perms
            )
        ]
    )
    engine._tool_registry.register_server_tools(
        "alpha",
        [Tool(name="echo", description="Echo", inputSchema={"type": "object"})],
    )
    engine._server_manager._statuses["alpha"] = ServerStatus(
        server_id="alpha", status="connected"
    )
    engine.call_tool = AsyncMock(side_effect=RuntimeError("boom"))

    missing_request = type(
        "Req", (), {"call_id": "1", "name": "missing.tool", "arguments": {}}
    )()
    failing_request = type(
        "Req",
        (),
        {"call_id": "2", "name": "alpha.echo", "arguments": {"text": "hi"}},
    )()

    results = await engine._execute_tool_requests(
        [missing_request, failing_request],
        active_servers=["alpha"],
    )

    assert len(results) == 2
    assert "Unknown or inactive MCP tool" in (results[0].error or "")
    assert results[1].namespace == "alpha.echo"
    assert results[1].error == "boom"


@pytest.mark.asyncio
async def test_mcp_client_engine_get_health_snapshot_counts_server_states() -> None:
    allow_perms = ServerPermissionConfig(default_mode=PermissionMode.ALLOW)
    engine = MCPClientEngine(
        servers=[
            ConfiguredServer(
                server_id="connected", command="python", permissions=allow_perms
            ),
            ConfiguredServer(
                server_id="stopped", command="python", permissions=allow_perms
            ),
            ConfiguredServer(
                server_id="disabled",
                command="python",
                enabled=False,
                permissions=allow_perms,
            ),
            ConfiguredServer(
                server_id="errored", command="python", permissions=allow_perms
            ),
        ]
    )
    engine._tool_registry.register_server_tools(
        "connected",
        [Tool(name="echo", description="Echo", inputSchema={"type": "object"})],
    )
    engine._server_manager._statuses = {
        "connected": ServerStatus(
            server_id="connected", status="connected", transport="stdio"
        ),
        "stopped": ServerStatus(
            server_id="stopped", status="stopped", transport="stdio"
        ),
        "disabled": ServerStatus(
            server_id="disabled", status="disabled", transport="stdio"
        ),
        "errored": ServerStatus(
            server_id="errored", status="error", error="boom", transport="stdio"
        ),
    }
    engine._server_manager._connections = {"connected": MagicMock()}
    engine._server_manager.check_health = AsyncMock(
        return_value=ServerStatus(
            server_id="connected",
            status="connected",
            transport="stdio",
            latency_ms=12.5,
            last_checked_at=1.0,
            last_connected_at=1.0,
        )
    )

    snapshot = await engine.get_health_snapshot()

    assert snapshot["status"] == "degraded"
    assert snapshot["summary"]["connected"] == 1
    assert snapshot["summary"]["stopped"] == 1
    assert snapshot["summary"]["disabled"] == 1
    assert snapshot["summary"]["error"] == 1
    connected = next(
        item for item in snapshot["servers"] if item["server_id"] == "connected"
    )
    assert connected["tool_count"] == 1
    assert connected["tools"] == ["connected.echo"]


@pytest.mark.asyncio
async def test_mcp_client_engine_require_connection_handles_disabled_and_unknown() -> (
    None
):
    engine = MCPClientEngine(
        servers=[
            ConfiguredServer(server_id="disabled", command="python", enabled=False)
        ]
    )

    with pytest.raises(PermissionError):
        await engine._require_connection("disabled")

    with pytest.raises(KeyError):
        await engine._require_connection("missing")
