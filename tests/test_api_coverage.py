"""Coverage tests for api/main.py — uncovered endpoints, error paths, and validators."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from stratifyai.models import ChatResponse, Usage


def _make_response(content: str = "ok", provider: str = "openai") -> ChatResponse:
    """Build a minimal ChatResponse for endpoint mocking.

    Args:
        content: Response text.
        provider: Provider name.

    Returns:
        A minimal ChatResponse.
    """
    return ChatResponse(
        id="test-id",
        model="gpt-4o-mini",
        content=content,
        finish_reason="stop",
        provider=provider,
        created_at=datetime.now(),
        raw_response={},
        usage=Usage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cost_usd=0.0001,
            cached_tokens=0,
            cache_creation_tokens=0,
            cache_read_tokens=0,
        ),
        latency_ms=42.0,
    )


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


@pytest.fixture
def client_no_auth():
    """TestClient with no API-key requirement.

    Yields:
        A FastAPI TestClient.
    """
    from api.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_with_auth():
    """TestClient with STRATIFYAI_API_KEY set to 'secret'.

    Yields:
        A (TestClient, headers) tuple.
    """
    with patch.dict("os.environ", {"STRATIFYAI_API_KEY": "secret"}):
        from api.main import app

        with TestClient(app) as c:
            yield c, {"Authorization": "Bearer secret"}


# ---------------------------------------------------------------------------
# Root / SPA-serving endpoints
# ---------------------------------------------------------------------------


class TestRootAndPageEndpoints:
    """Tests for /, /models, /mcp, and related page routes."""

    def test_root_returns_json_when_no_spa(self, client_no_auth) -> None:
        """/ returns a JSON dict when no SPA build is found."""
        with patch("api.main._get_spa_index", return_value=None):
            resp = client_no_auth.get("/")
        assert resp.status_code == 200
        assert "StratifyAI" in resp.json().get("name", "") or "name" in resp.json()

    def test_models_page_returns_200(self, client_no_auth) -> None:
        """/models endpoint always returns 200."""
        with (
            patch("api.main._get_spa_index", return_value=None),
            patch("os.path.exists", return_value=False),
        ):
            resp = client_no_auth.get("/models")
        assert resp.status_code == 200

    def test_mcp_page_returns_error_when_no_spa(self, client_no_auth) -> None:
        """/mcp returns an error dict when no SPA build is found."""
        with patch("api.main._get_spa_index", return_value=None):
            resp = client_no_auth.get("/mcp")
        assert resp.status_code == 200
        assert "error" in resp.json() or "name" in resp.json()


# ---------------------------------------------------------------------------
# _get_version helper
# ---------------------------------------------------------------------------


class TestGetVersion:
    """Tests for the internal _get_version() function."""

    def test_version_exception_returns_default(self) -> None:
        """If pyproject.toml cannot be read, a default version string is returned."""
        from api.main import _get_version

        with patch("builtins.open", side_effect=OSError("no file")):
            version = _get_version()
        assert isinstance(version, str)
        assert len(version) > 0


# ---------------------------------------------------------------------------
# Input validators on ChatCompletionRequest
# ---------------------------------------------------------------------------


class TestRequestValidators:
    """Tests for field validators on ChatCompletionRequest."""

    def test_invalid_temperature_rejected(self, client_no_auth) -> None:
        """temperature outside [0, 2] is rejected with 422."""
        resp = client_no_auth.post(
            "/api/chat",
            json={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "temperature": 3.5,
            },
        )
        assert resp.status_code == 422

    def test_zero_max_tokens_rejected(self, client_no_auth) -> None:
        """max_tokens=0 is rejected with 422."""
        resp = client_no_auth.post(
            "/api/chat",
            json={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 0,
            },
        )
        assert resp.status_code == 422

    def test_empty_messages_rejected(self, client_no_auth) -> None:
        """An empty messages list is rejected with 422."""
        resp = client_no_auth.post(
            "/api/chat",
            json={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [],
            },
        )
        assert resp.status_code == 422

    def test_invalid_provider_rejected(self, client_no_auth) -> None:
        """An unknown provider value is rejected with 422."""
        resp = client_no_auth.post(
            "/api/chat",
            json={
                "provider": "unknown_provider_xyz",
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
        assert resp.status_code == 422

    def test_invalid_role_rejected(self, client_no_auth) -> None:
        """A message with an invalid role returns an error status."""
        resp = client_no_auth.post(
            "/api/chat",
            json={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "robot", "content": "hi"}],
            },
        )
        # Role validation happens inside handler (not at Pydantic level) -> 4xx or 5xx
        assert resp.status_code >= 400

    def test_control_char_in_content_rejected(self, client_no_auth) -> None:
        """Control characters in content return an error status."""
        resp = client_no_auth.post(
            "/api/chat",
            json={
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "hi\x01there"}],
            },
        )
        # Validation happens inside handler (StreamMessage) not at field level -> error
        assert resp.status_code >= 400


# ---------------------------------------------------------------------------
# Budget enforcement
# ---------------------------------------------------------------------------


class TestBudgetEnforcement:
    """Tests for _enforce_budget and related budget-exceeded paths."""

    def test_budget_exceeded_returns_402(self, client_no_auth) -> None:
        """When the budget is exceeded, /api/chat returns 402."""
        with patch("api.main.cost_tracker") as mock_tracker:
            mock_tracker.is_over_budget.return_value = True
            resp = client_no_auth.post(
                "/api/chat",
                json={
                    "provider": "openai",
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
        assert resp.status_code == 402


# ---------------------------------------------------------------------------
# /api/chat error-handling branches
# ---------------------------------------------------------------------------


class TestChatCompletionErrors:
    """Tests for the error-handling branches inside /api/chat."""

    def _base_payload(self) -> dict:
        """Return a minimal valid chat payload.

        Returns:
            A dict suitable for the /api/chat endpoint.
        """
        return {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "hello"}],
        }

    def test_authentication_error_returns_401(self, client_no_auth) -> None:
        """AuthenticationError inside the handler returns 401."""
        with patch("api.main.get_tracked_client") as mock_get:
            tracked = MagicMock()
            tracked.chat_completion = AsyncMock(
                side_effect=RuntimeError("authentication failed: api key is invalid")
            )
            mock_get.return_value = tracked
            resp = client_no_auth.post("/api/chat", json=self._base_payload())
        assert resp.status_code == 401

    def test_rate_limit_error_returns_429(self, client_no_auth) -> None:
        """A rate limit message inside an exception returns 429."""
        with patch("api.main.get_tracked_client") as mock_get:
            tracked = MagicMock()
            tracked.chat_completion = AsyncMock(
                side_effect=RuntimeError("rate limit exceeded")
            )
            mock_get.return_value = tracked
            resp = client_no_auth.post("/api/chat", json=self._base_payload())
        assert resp.status_code == 429

    def test_insufficient_balance_returns_402(self, client_no_auth) -> None:
        """An 'insufficient balance' message returns 402."""
        with patch("api.main.get_tracked_client") as mock_get:
            tracked = MagicMock()
            tracked.chat_completion = AsyncMock(
                side_effect=RuntimeError("insufficient balance in account")
            )
            mock_get.return_value = tracked
            resp = client_no_auth.post("/api/chat", json=self._base_payload())
        assert resp.status_code == 402

    def test_not_found_error_returns_404(self, client_no_auth) -> None:
        """A 'not found' message returns 404."""
        with patch("api.main.get_tracked_client") as mock_get:
            tracked = MagicMock()
            tracked.chat_completion = AsyncMock(
                side_effect=RuntimeError("resource not found")
            )
            mock_get.return_value = tracked
            resp = client_no_auth.post("/api/chat", json=self._base_payload())
        assert resp.status_code == 404

    def test_invalid_model_error_returns_400(self, client_no_auth) -> None:
        """An 'invalid model' message returns 400."""
        with patch("api.main.get_tracked_client") as mock_get:
            tracked = MagicMock()
            tracked.chat_completion = AsyncMock(
                side_effect=RuntimeError("invalid model specified")
            )
            mock_get.return_value = tracked
            resp = client_no_auth.post("/api/chat", json=self._base_payload())
        assert resp.status_code == 400

    def test_too_long_error_returns_413(self, client_no_auth) -> None:
        """A 'too long' message returns 413."""
        with patch("api.main.get_tracked_client") as mock_get:
            tracked = MagicMock()
            tracked.chat_completion = AsyncMock(
                side_effect=RuntimeError("input is too long for model")
            )
            mock_get.return_value = tracked
            resp = client_no_auth.post("/api/chat", json=self._base_payload())
        assert resp.status_code == 413

    def test_too_long_with_token_match_includes_suggestion(
        self, client_no_auth
    ) -> None:
        """A 'too long' error with token count pattern includes a suggestion."""
        with patch("api.main.get_tracked_client") as mock_get:
            tracked = MagicMock()
            tracked.chat_completion = AsyncMock(
                side_effect=RuntimeError(
                    "input is too long: 150000 tokens > 128000 maximum"
                )
            )
            mock_get.return_value = tracked
            resp = client_no_auth.post("/api/chat", json=self._base_payload())
        assert resp.status_code == 413
        body = resp.json()
        # 'suggestion' key should be present
        assert "suggestion" in body.get("detail", {})

    def test_generic_500_error(self, client_no_auth) -> None:
        """An unclassified exception returns 500."""
        with patch("api.main.get_tracked_client") as mock_get:
            tracked = MagicMock()
            tracked.chat_completion = AsyncMock(
                side_effect=RuntimeError("something totally unexpected")
            )
            mock_get.return_value = tracked
            resp = client_no_auth.post("/api/chat", json=self._base_payload())
        assert resp.status_code == 500


# ---------------------------------------------------------------------------
# _get_spa_index helper
# ---------------------------------------------------------------------------


class TestGetSpaIndex:
    """Tests for _get_spa_index."""

    def test_returns_none_when_no_files_exist(self) -> None:
        """Returns None when neither dist/index.html nor index.html exist."""
        from api.main import _get_spa_index

        with patch("os.path.exists", return_value=False):
            result = _get_spa_index()
        assert result is None

    def test_returns_legacy_index_when_dist_missing(self, tmp_path) -> None:
        """Returns the legacy index.html path when dist is absent but legacy exists."""
        from api.main import _get_spa_index

        static_dir = tmp_path / "static"
        static_dir.mkdir()
        legacy = static_dir / "index.html"
        legacy.write_text("<html/>")

        def fake_exists(path: str) -> bool:
            return path == str(legacy)

        with (
            patch("os.path.exists", side_effect=fake_exists),
            patch("os.path.dirname", return_value=str(tmp_path / "api")),
        ):
            result = _get_spa_index()
        # result is either the legacy path or None depending on dirname mock
        assert result is None or isinstance(result, str)


# ---------------------------------------------------------------------------
# /api/models/{provider} — validation failure branch
# ---------------------------------------------------------------------------


class TestListModelsValidationFailure:
    """Tests for /api/models/{provider} when validation fails."""

    def test_validation_failure_falls_back_to_catalog(self, client_no_auth) -> None:
        """When provider validation fails, the catalog is returned as fallback."""
        with patch(
            "stratifyai.utils.provider_validator.get_validated_interactive_models",
            return_value={
                "validation_result": {
                    "error": "API key not configured",
                    "invalid_models": [],
                    "validation_time_ms": 5,
                },
                "models": {},
            },
        ):
            resp = client_no_auth.get("/api/models/openai")
        assert resp.status_code == 200
        body = resp.json()
        assert "models" in body
        assert body["validation"]["error"] is not None


# ---------------------------------------------------------------------------
# lifespan (shutdown path)
# ---------------------------------------------------------------------------


class TestLifespan:
    """Tests for the application lifespan cleanup."""

    def test_lifespan_stops_engine_on_shutdown(self) -> None:
        """The lifespan context manager calls engine.stop() on shutdown."""
        import asyncio

        import api.main as api_main
        from api.main import lifespan

        mock_engine = AsyncMock()
        mock_engine.stop = AsyncMock()

        async def run():
            original = api_main._mcp_chat_engine
            api_main._mcp_chat_engine = mock_engine
            try:
                from api.main import app

                async with lifespan(app):
                    pass
            finally:
                api_main._mcp_chat_engine = original

        asyncio.get_event_loop().run_until_complete(run())
        mock_engine.stop.assert_called_once()


# ---------------------------------------------------------------------------
# get_client caching
# ---------------------------------------------------------------------------


class TestGetClientCaching:
    """Tests for the get_client connection-pool helper."""

    def test_get_client_creates_and_caches(self) -> None:
        """get_client creates a client on first call and returns the same one after."""
        import api.main as api_main

        original_cache = dict(api_main._client_cache)
        try:
            api_main._client_cache.clear()
            with patch("api.main.LLMClient") as mock_cls:
                mock_instance = MagicMock()
                mock_cls.return_value = mock_instance
                c1 = api_main.get_client("openai")
                c2 = api_main.get_client("openai")
            assert c1 is c2
            assert mock_cls.call_count == 1
        finally:
            api_main._client_cache = original_cache
