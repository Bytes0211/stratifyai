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
