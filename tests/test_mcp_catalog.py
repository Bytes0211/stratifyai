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
                }
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

    async def fake_get_mcp_chat_engine():
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
