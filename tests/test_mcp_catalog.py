"""Tests for MCP catalog management and CLI setup workflow."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from typer.testing import CliRunner

from cli.stratifyai_cli import app

runner = CliRunner()


def test_mcp_list_outputs_known_servers() -> None:
    result = runner.invoke(app, ["mcp", "list"])

    assert result.exit_code == 0
    assert "stratifyai" in result.output.lower()
    assert "filesystem" in result.output.lower()


def test_mcp_setup_dry_run_outputs_cursor_config(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "mcp",
            "setup",
            "--client",
            "cursor",
            "--servers",
            "stratifyai,filesystem",
            "--env",
            "OPENAI_API_KEY=sk-test",
            "--arg",
            "filesystem.paths=/tmp",
            "--project-root",
            str(tmp_path),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert '"mcpServers"' in result.output
    assert '"stratifyai"' in result.output
    assert '"filesystem"' in result.output


def test_manager_builds_vscode_config() -> None:
    from stratifyai.mcp_catalog.manager import build_client_config

    config = build_client_config(
        client="vscode",
        server_ids=["stratifyai"],
        env_values={"OPENAI_API_KEY": "sk-test"},
        arg_values={},
    )

    assert "mcp" in config
    assert "servers" in config["mcp"]
    assert "stratifyai" in config["mcp"]["servers"]


def test_manager_normalizes_database_url_for_postgres_config() -> None:
    from stratifyai.mcp_catalog.manager import build_client_config

    config = build_client_config(
        client="cursor",
        server_ids=["postgresql"],
        env_values={
            "DATABASE_URL": 'DATABASE_URL="postgresql://scotton:autocorp@localhost:5432/autocorp"'
        },
        arg_values={},
    )

    assert (
        config["mcpServers"]["postgresql"]["env"]["DATABASE_URL"]
        == "postgresql://scotton:autocorp@localhost:5432/autocorp"
    )


def test_write_client_config_merges_and_creates_backup(tmp_path: Path) -> None:
    from stratifyai.mcp_catalog.manager import build_client_config, write_client_config

    output_path = tmp_path / "mcp.json"
    output_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "existing": {"command": "npx", "args": ["existing-server"]}
                }
            }
        ),
        encoding="utf-8",
    )

    config = build_client_config(
        client="cursor",
        server_ids=["stratifyai"],
        env_values={"OPENAI_API_KEY": "sk-test"},
        arg_values={},
        project_root=tmp_path,
    )

    written_path = write_client_config(
        client="cursor",
        config=config,
        output_path=output_path,
    )

    merged = json.loads(written_path.read_text(encoding="utf-8"))
    assert "existing" in merged["mcpServers"]
    assert "stratifyai" in merged["mcpServers"]
    assert output_path.with_suffix(".json.backup").exists()


def test_write_mcp_client_settings_persists_permissions_metadata(
    tmp_path: Path,
) -> None:
    from stratifyai.mcp_catalog.manager import (
        get_mcp_client_settings,
        write_mcp_client_settings,
    )

    output_path = tmp_path / ".cursor" / "mcp.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"mcpServers": {"github": {"command": "npx", "args": ["github"]}}}),
        encoding="utf-8",
    )

    write_mcp_client_settings(
        client="cursor",
        settings={
            "servers": {
                "github": {
                    "enabled": True,
                    "auto_start": False,
                    "permissions": {"confirm": ["create_*"], "deny": ["delete_*"]},
                }
            }
        },
        output_path=output_path,
    )

    _path, settings = get_mcp_client_settings(client="cursor", output_path=output_path)
    assert settings["servers"]["github"]["auto_start"] is False
    assert settings["servers"]["github"]["permissions"]["confirm"] == ["create_*"]
    merged = json.loads(output_path.read_text(encoding="utf-8"))
    assert "mcpServers" in merged
    assert merged["stratifyai"]["mcpClient"]["servers"]["github"]["enabled"] is True


def test_validate_prerequisites_warns_for_missing_npx(monkeypatch) -> None:
    from stratifyai.mcp_catalog.manager import validate_prerequisites

    monkeypatch.setattr("stratifyai.mcp_catalog.manager.shutil.which", lambda _: None)

    warnings = validate_prerequisites(["github"])
    assert any("Node.js" in warning or "npx" in warning for warning in warnings)


def test_mcp_status_shows_configured_servers(tmp_path: Path) -> None:
    config_path = tmp_path / ".cursor" / "mcp.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {"mcpServers": {"github": {"command": "npx", "args": ["-y", "github-mcp"]}}}
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "mcp",
            "status",
            "--client",
            "cursor",
            "--project-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "github" in result.output.lower()
    assert "configured" in result.output.lower()


def test_mcp_add_writes_single_server(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "mcp",
            "add",
            "tavily",
            "--client",
            "cursor",
            "--project-root",
            str(tmp_path),
            "--env",
            "TAVILY_API_KEY=tvly-test",
        ],
    )

    assert result.exit_code == 0
    written = json.loads(
        (tmp_path / ".cursor" / "mcp.json").read_text(encoding="utf-8")
    )
    assert "tavily" in written["mcpServers"]
    assert written["mcpServers"]["tavily"]["env"]["TAVILY_API_KEY"] == "tvly-test"


def test_mcp_add_custom_writes_custom_server(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "mcp",
            "add-custom",
            "demo-custom",
            "--client",
            "cursor",
            "--project-root",
            str(tmp_path),
            "--command",
            "python",
            "--command-arg",
            "-m",
            "--command-arg",
            "demo.server",
            "--env",
            "DEMO_TOKEN=secret",
        ],
    )

    assert result.exit_code == 0
    written = json.loads(
        (tmp_path / ".cursor" / "mcp.json").read_text(encoding="utf-8")
    )
    assert written["mcpServers"]["demo-custom"]["command"] == "python"
    assert written["mcpServers"]["demo-custom"]["args"] == ["-m", "demo.server"]
    assert written["mcpServers"]["demo-custom"]["env"]["DEMO_TOKEN"] == "secret"


def test_mcp_remove_deletes_server_from_config(tmp_path: Path) -> None:
    config_path = tmp_path / ".cursor" / "mcp.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "github": {"command": "npx", "args": ["-y", "github-mcp"]},
                    "memory": {"command": "npx", "args": ["-y", "memory-mcp"]},
                },
                "stratifyai": {
                    "mcpClient": {
                        "servers": {
                            "github": {"enabled": True, "auto_start": False},
                            "memory": {"enabled": True, "auto_start": True},
                        }
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "mcp",
            "remove",
            "github",
            "--client",
            "cursor",
            "--project-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    written = json.loads(config_path.read_text(encoding="utf-8"))
    assert "github" not in written["mcpServers"]
    assert "memory" in written["mcpServers"]
    assert "github" not in written["stratifyai"]["mcpClient"]["servers"]


def test_api_mcp_catalog_returns_curated_servers() -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    client = TestClient(api_app)
    response = client.get("/api/mcp/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"]
    assert any(server["id"] == "stratifyai" for server in payload["servers"])


def test_api_mcp_clients_returns_supported_targets(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    client = TestClient(api_app)
    response = client.get("/api/mcp/clients", params={"project_root": str(tmp_path)})

    assert response.status_code == 200
    payload = response.json()
    assert any(item["id"] == "cursor" for item in payload["clients"])
    assert any(item["id"] == "vscode" for item in payload["clients"])


def test_api_mcp_configure_preview_returns_config(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    client = TestClient(api_app)
    response = client.post(
        "/api/mcp/configure",
        json={
            "client": "cursor",
            "server_ids": ["stratifyai", "filesystem"],
            "env_values": {"OPENAI_API_KEY": "sk-test"},
            "arg_values": {"filesystem.paths": str(tmp_path)},
            "project_root": str(tmp_path),
            "apply": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["applied"] is False
    assert "mcpServers" in payload["config"]
    assert "filesystem" in payload["config"]["mcpServers"]


def test_api_mcp_configure_normalizes_database_url_value(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    client = TestClient(api_app)
    response = client.post(
        "/api/mcp/configure",
        json={
            "client": "claude-desktop",
            "server_ids": ["postgresql"],
            "env_values": {
                "DATABASE_URL": '"postgresql://scotton:autocorp@localhost:5432/autocorp"'
            },
            "project_root": str(tmp_path),
            "apply": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["config"]["mcpServers"]["postgresql"]["env"]["DATABASE_URL"]
        == "postgresql://scotton:autocorp@localhost:5432/autocorp"
    )


def test_api_mcp_reset_clears_all_configured_servers(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    config_path = tmp_path / ".cursor" / "mcp.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "memory": {"command": "npx", "args": ["-y", "memory-mcp"]}
                },
                "stratifyai": {
                    "mcpClient": {
                        "servers": {"memory": {"enabled": True, "auto_start": True}}
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    client = TestClient(api_app)
    response = client.post(
        "/api/mcp/reset",
        json={
            "client": "cursor",
            "project_root": str(tmp_path),
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["removed_server_ids"] == ["memory"]

    written = json.loads(config_path.read_text(encoding="utf-8"))
    assert written["mcpServers"] == {}
    assert written["stratifyai"]["mcpClient"]["servers"] == {}


def test_api_mcp_status_reads_existing_config(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    config_path = tmp_path / ".cursor" / "mcp.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {"mcpServers": {"memory": {"command": "npx", "args": ["-y", "memory-mcp"]}}}
        ),
        encoding="utf-8",
    )

    client = TestClient(api_app)
    response = client.get(
        "/api/mcp/status",
        params={"client": "cursor", "project_root": str(tmp_path)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert "memory" in payload["configured"]


def test_api_mcp_tools_returns_tool_metadata() -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    client = TestClient(api_app)
    response = client.get("/api/mcp/tools")

    assert response.status_code == 200
    payload = response.json()
    assert any(tool["name"] == "list_providers" for tool in payload["tools"])
    assert any(tool["name"] == "chat_completion" for tool in payload["tools"])


def test_api_mcp_test_tool_executes_list_providers() -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    client = TestClient(api_app)
    response = client.post(
        "/api/mcp/test-tool",
        json={"tool_name": "list_providers", "payload": {}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["tool_name"] == "list_providers"
    assert isinstance(payload["result"], list)
    assert any(item["provider"] == "openai" for item in payload["result"])


def test_api_chat_with_active_mcp_servers_returns_tool_metadata(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app
    from stratifyai.models import ChatResponse, Usage

    tracked = MagicMock()
    tracked.chat_with_mcp = AsyncMock(
        return_value=ChatResponse(
            id="chat-mcp-1",
            provider="openai",
            model="gpt-4.1-mini",
            content="Answer with MCP help",
            finish_reason="stop",
            usage=Usage(prompt_tokens=11, completion_tokens=7, total_tokens=18),
            created_at=datetime.now(),
            raw_response={
                "mcp_warnings": ["demo offline"],
                "mcp_tool_results": [{"namespace": "demo.echo"}],
                "mcp_active_servers": ["demo"],
            },
        )
    )

    monkeypatch.setattr("api.main.get_tracked_client", lambda _: tracked)

    async def fake_get_mcp_chat_engine(refresh: bool = False):
        del refresh
        return object()

    monkeypatch.setattr("api.main.get_mcp_chat_engine", fake_get_mcp_chat_engine)

    client = TestClient(api_app)
    response = client.post(
        "/api/chat",
        json={
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "messages": [{"role": "user", "content": "hello"}],
            "active_mcp_servers": ["demo"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["warnings"] == ["demo offline"]
    assert payload["tool_results"][0]["namespace"] == "demo.echo"
    assert payload["active_mcp_servers"] == ["demo"]
    tracked.chat_with_mcp.assert_awaited_once()


def test_api_mcp_client_servers_and_tools_return_runtime_metadata(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app
    from stratifyai.mcp_client.config import ConfiguredServer
    from stratifyai.mcp_client.permissions import (
        PermissionManager,
        ServerPermissionConfig,
    )
    from stratifyai.mcp_client.server_manager import ServerStatus
    from stratifyai.mcp_client.tool_registry import ToolDescriptor

    class FakeEngine:
        def __init__(self) -> None:
            self._servers = [
                ConfiguredServer(
                    server_id="demo",
                    command="python",
                    enabled=True,
                    auto_start=False,
                    permissions=ServerPermissionConfig(confirm=["delete_*"]),
                )
            ]
            self._server_index = {server.server_id: server for server in self._servers}
            self._permission_manager = PermissionManager(
                {"demo": self._servers[0].permissions}
            )
            self.start_server = AsyncMock(
                return_value=ServerStatus(server_id="demo", status="connected")
            )
            self.stop_server = AsyncMock(
                return_value=ServerStatus(server_id="demo", status="stopped")
            )
            self.restart_server = AsyncMock(
                return_value=ServerStatus(server_id="demo", status="connected")
            )

        def list_servers(self):
            return [ServerStatus(server_id="demo", status="connected")]

        def list_tools(self):
            return [
                ToolDescriptor(
                    server_id="demo",
                    tool_name="delete_file",
                    namespace="demo.delete_file",
                    description="Delete a file",
                    input_schema={"type": "object"},
                )
            ]

        def find_tool(self, _server_id: str, _tool_name: str):
            return None

    fake_engine = FakeEngine()

    async def fake_get_mcp_chat_engine(refresh: bool = False):
        del refresh
        return fake_engine

    monkeypatch.setattr("api.main.get_mcp_chat_engine", fake_get_mcp_chat_engine)

    client = TestClient(api_app)

    servers_response = client.get("/api/mcp-client/servers")
    assert servers_response.status_code == 200
    servers_payload = servers_response.json()
    assert servers_payload["servers"][0]["server_id"] == "demo"
    assert servers_payload["servers"][0]["tool_count"] == 1
    assert servers_payload["servers"][0]["auto_start"] is False

    tools_response = client.get("/api/mcp-client/tools")
    assert tools_response.status_code == 200
    tools_payload = tools_response.json()
    assert tools_payload["tools"][0]["namespace"] == "demo.delete_file"
    assert tools_payload["tools"][0]["permission"] == "confirm"

    action_response = client.post("/api/mcp-client/servers/demo/restart")
    assert action_response.status_code == 200
    assert action_response.json()["status"] == "connected"
    fake_engine.restart_server.assert_awaited_once_with("demo")


def test_api_mcp_client_permissions_can_be_updated(tmp_path: Path) -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    config_path = tmp_path / ".cursor" / "mcp.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {"demo": {"command": "python", "args": ["-m", "demo"]}},
                "stratifyai": {"mcpClient": {"servers": {"demo": {"enabled": True}}}},
            }
        ),
        encoding="utf-8",
    )

    client = TestClient(api_app)

    get_response = client.get(
        "/api/mcp-client/permissions",
        params={"client": "cursor", "output_path": str(config_path)},
    )
    assert get_response.status_code == 200
    assert get_response.json()["servers"]["demo"]["enabled"] is True

    put_response = client.put(
        "/api/mcp-client/permissions",
        json={
            "client": "cursor",
            "output_path": str(config_path),
            "servers": {
                "demo": {
                    "enabled": False,
                    "auto_start": False,
                    "permissions": {
                        "allow": ["read_*"],
                        "confirm": ["delete_*"],
                    },
                }
            },
        },
    )

    assert put_response.status_code == 200
    payload = put_response.json()
    assert payload["servers"]["demo"]["enabled"] is False
    assert payload["servers"]["demo"]["permissions"]["confirm"] == ["delete_*"]

    written = json.loads(config_path.read_text(encoding="utf-8"))
    assert written["stratifyai"]["mcpClient"]["servers"]["demo"]["auto_start"] is False


def test_api_mcp_client_tool_execution_and_resource_fetch(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    class FakeEngine:
        def __init__(self) -> None:
            self.call_tool = AsyncMock(
                return_value={"content": [{"type": "text", "text": "ok"}]}
            )
            self.get_resource = AsyncMock(return_value="resource body")

    fake_engine = FakeEngine()

    async def fake_get_mcp_chat_engine(refresh: bool = False):
        del refresh
        return fake_engine

    monkeypatch.setattr("api.main.get_mcp_chat_engine", fake_get_mcp_chat_engine)

    client = TestClient(api_app)

    tool_response = client.post(
        "/api/mcp-client/tools/demo/list_files",
        json={"path": "/tmp"},
    )
    assert tool_response.status_code == 200
    tool_payload = tool_response.json()
    assert tool_payload["server_id"] == "demo"
    assert tool_payload["tool_name"] == "list_files"
    assert tool_payload["arguments"] == {"path": "/tmp"}
    assert tool_payload["result"]["content"][0]["text"] == "ok"
    fake_engine.call_tool.assert_awaited_once_with(
        "demo", "list_files", {"path": "/tmp"}
    )

    resource_response = client.get(
        "/api/mcp-client/resources/demo/stratifyai%3A%2F%2Fcatalog"
    )
    assert resource_response.status_code == 200
    resource_payload = resource_response.json()
    assert resource_payload["server_id"] == "demo"
    assert resource_payload["uri"] == "stratifyai://catalog"
    assert resource_payload["content"] == "resource body"
    fake_engine.get_resource.assert_awaited_once_with("demo", "stratifyai://catalog")


def test_api_mcp_client_health_reports_diagnostics(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from api.main import app as api_app

    class FakeEngine:
        def __init__(self) -> None:
            self.get_health_snapshot = AsyncMock(
                return_value={
                    "status": "degraded",
                    "checked_at": "2026-04-04T12:00:00Z",
                    "summary": {
                        "total": 2,
                        "connected": 1,
                        "degraded": 1,
                        "stopped": 0,
                        "disabled": 0,
                    },
                    "servers": [
                        {
                            "server_id": "demo",
                            "status": "connected",
                            "latency_ms": 12.5,
                            "last_checked_at": "2026-04-04T12:00:00Z",
                            "error": None,
                        },
                        {
                            "server_id": "broken",
                            "status": "error",
                            "latency_ms": None,
                            "last_checked_at": "2026-04-04T12:00:00Z",
                            "error": "boom",
                        },
                    ],
                }
            )

    fake_engine = FakeEngine()

    async def fake_get_mcp_chat_engine(refresh: bool = False):
        del refresh
        return fake_engine

    monkeypatch.setattr("api.main.get_mcp_chat_engine", fake_get_mcp_chat_engine)

    client = TestClient(api_app)
    response = client.get("/api/mcp-client/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["summary"]["connected"] == 1
    assert payload["servers"][1]["error"] == "boom"
    fake_engine.get_health_snapshot.assert_awaited_once_with()
