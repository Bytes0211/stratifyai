"""Additional FastAPI endpoint coverage for templates and MCP diagnostics."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


@patch.dict("os.environ", {"STRATIFYAI_API_KEY": "api-secret"})
def test_template_endpoints_list_get_and_render():
    from api.main import app

    client = TestClient(app)
    headers = {"Authorization": "Bearer api-secret"}

    list_resp = client.get("/api/templates", headers=headers)
    detail_resp = client.get("/api/templates/summarize", headers=headers)
    render_resp = client.post(
        "/api/templates/summarize/render",
        json={"params": {"text": "Housing prices rose.", "style": "bullet_points"}},
        headers=headers,
    )

    assert list_resp.status_code == 200
    assert any(item["name"] == "summarize" for item in list_resp.json())
    assert detail_resp.status_code == 200
    assert detail_resp.json()["name"] == "summarize"
    assert render_resp.status_code == 200
    assert render_resp.json()[0]["role"] == "system"
    assert "Housing prices rose." in render_resp.json()[1]["content"]


@patch.dict("os.environ", {"STRATIFYAI_API_KEY": "api-secret"})
@patch("api.main.get_mcp_chat_engine", new_callable=AsyncMock)
def test_mcp_client_servers_endpoint_formats_runtime_timestamps(mock_get_engine):
    from api.main import app

    engine = MagicMock()
    engine.list_tools.return_value = []
    engine._server_index = {
        "demo": MagicMock(enabled=True, auto_start=True, source_client="claude-desktop")
    }
    engine.list_servers.return_value = [
        MagicMock(
            server_id="demo",
            status="connected",
            error=None,
            transport="stdio",
            latency_ms=4.2,
            last_checked_at=1775413645.2024734,
            last_connected_at=1775413645.2024734,
        )
    ]
    mock_get_engine.return_value = engine

    client = TestClient(app)
    resp = client.get(
        "/api/mcp-client/servers?refresh=true",
        headers={"Authorization": "Bearer api-secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["servers"][0]["last_checked_at"].endswith("Z")
    assert body["servers"][0]["last_connected_at"].endswith("Z")


@patch.dict("os.environ", {"STRATIFYAI_API_KEY": "api-secret"})
@patch("api.main.get_mcp_chat_engine", new_callable=AsyncMock)
def test_mcp_client_health_endpoint_returns_snapshot(mock_get_engine):
    from api.main import app

    engine = MagicMock()
    engine.get_health_snapshot = AsyncMock(
        return_value={
            "status": "healthy",
            "checked_at": "2026-04-05T00:00:00Z",
            "summary": {"total": 2, "connected": 1, "failed": 0},
            "servers": [
                {
                    "server_id": "demo",
                    "status": "connected",
                    "transport": "stdio",
                    "latency_ms": 4.2,
                }
            ],
        }
    )
    mock_get_engine.return_value = engine

    client = TestClient(app)
    resp = client.get(
        "/api/mcp-client/health",
        headers={"Authorization": "Bearer api-secret"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["summary"]["connected"] == 1
    assert body["servers"][0]["server_id"] == "demo"


@patch.dict("os.environ", {"STRATIFYAI_API_KEY": "api-secret"})
@patch("api.main.get_mcp_chat_engine", new_callable=AsyncMock)
def test_mcp_client_tool_execution_sanitizes_errors(mock_get_engine):
    from api.main import app

    engine = MagicMock()
    engine.call_tool = AsyncMock(
        side_effect=RuntimeError("tool failed for sk-proj-ABCDEFGHIJKLMNOP")
    )
    mock_get_engine.return_value = engine

    client = TestClient(app)
    resp = client.post(
        "/api/mcp-client/tools/demo/run",
        json={"arg": "value"},
        headers={"Authorization": "Bearer api-secret"},
    )

    assert resp.status_code == 400
    assert "sk-proj-ABCDEFGHIJKLMNOP" not in resp.text
    assert "REDACTED" in resp.text


@patch.dict("os.environ", {"STRATIFYAI_API_KEY": "api-secret"})
def test_mcp_client_servers_endpoint_does_not_autostart_on_first_load():
    import api.main as api_main
    from api.main import app

    client = TestClient(app)
    headers = {"Authorization": "Bearer api-secret"}

    original_engine = api_main._mcp_chat_engine
    api_main._mcp_chat_engine = None

    with patch(
        "api.main.MCPClientEngine.start",
        new=AsyncMock(side_effect=RuntimeError("should not start")),
    ):
        resp = client.get("/api/mcp-client/servers?refresh=true", headers=headers)

    api_main._mcp_chat_engine = original_engine

    assert resp.status_code == 200
    assert "servers" in resp.json()


@patch.dict("os.environ", {"STRATIFYAI_API_KEY": "api-secret"})
def test_versioned_api_aliases_and_file_size_limits():
    import api.main as api_main
    from api.main import app

    client = TestClient(app)
    headers = {"Authorization": "Bearer api-secret"}

    versioned_health = client.get("/v1/health")
    assert versioned_health.status_code == 200
    assert versioned_health.json() == {"status": "healthy"}

    versioned_templates = client.get("/v1/templates", headers=headers)
    assert versioned_templates.status_code == 200

    with patch.object(api_main, "_MAX_FILE_PAYLOAD_CHARS", 10):
        resp = client.post(
            "/api/chat",
            json={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "file_name": "notes.txt",
                "file_content": "x" * 11,
            },
            headers=headers,
        )

    assert resp.status_code == 413
    assert resp.json()["detail"]["error"] == "file_too_large"
