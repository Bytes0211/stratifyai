"""Tests for P0 (WebSocket token-limit parity) and P1 (per-entry cache TTL).

P0 — _check_token_limits helper
    Covers: system limit, model/API limit, and pass-through cases.

P1 — Per-entry TTL for ResponseCache, PersistentResponseCache, and
     the cache_response decorator.
"""

import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from stratifyai.caching import (
    PersistentResponseCache,
    ResponseCache,
    cache_response,
)
from stratifyai.models import ChatResponse, Message, Usage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_response(content: str = "ok", model: str = "gpt-4.1-mini") -> ChatResponse:
    return ChatResponse(
        id="r1",
        model=model,
        content=content,
        finish_reason="stop",
        usage=Usage(
            prompt_tokens=10, completion_tokens=5, total_tokens=15, cost_usd=0.001
        ),
        provider="openai",
        created_at=datetime.now(),
        raw_response={},
    )


def _messages():
    return [Message(role="user", content="Hello")]


# ---------------------------------------------------------------------------
# P0 — _check_token_limits
# ---------------------------------------------------------------------------


class TestCheckTokenLimits:
    """Unit tests for the _check_token_limits helper in api.main."""

    def _import_helper(self):
        """Lazily import to avoid FastAPI startup side-effects in other tests."""
        from api.main import _check_token_limits  # noqa: PLC0415

        return _check_token_limits

    @patch("api.main.MODEL_CATALOG", {"openai": {"gpt-4.1-mini": {}}})
    @patch("api.main.count_tokens_for_messages", return_value=100, create=True)
    @patch("api.main.get_context_window", return_value=128_000, create=True)
    def test_passes_when_within_limit(self, mock_ctx, mock_tokens):
        """No exception for normal-sized inputs."""
        # Patch the inner imports used by the helper
        with (
            patch(
                "stratifyai.utils.token_counter.count_tokens_for_messages",
                return_value=100,
            ),
            patch(
                "stratifyai.utils.token_counter.get_context_window",
                return_value=128_000,
            ),
        ):
            fn = self._import_helper()
            # Should not raise
            fn(_messages(), "openai", "gpt-4.1-mini")

    def test_raises_413_for_system_limit(self):
        """Raises HTTPException 413 with error='content_too_large' when > 1M tokens."""
        fn = self._import_helper()
        with (
            patch(
                "stratifyai.utils.token_counter.count_tokens_for_messages",
                return_value=2_000_000,
            ),
            patch(
                "stratifyai.utils.token_counter.get_context_window",
                return_value=1_000_000,
            ),
            patch("api.main.MODEL_CATALOG", {"openai": {"gpt-4.1-mini": {}}}),
        ):
            with pytest.raises(HTTPException) as exc_info:
                fn(_messages(), "openai", "gpt-4.1-mini")
        assert exc_info.value.status_code == 413
        assert exc_info.value.detail["error"] == "content_too_large"
        assert exc_info.value.detail["estimated_tokens"] == 2_000_000

    def test_raises_413_for_model_limit(self):
        """Raises HTTPException 413 with error='input_too_long' when > model limit."""
        fn = self._import_helper()
        with (
            patch(
                "stratifyai.utils.token_counter.count_tokens_for_messages",
                return_value=200_000,
            ),
            patch(
                "stratifyai.utils.token_counter.get_context_window",
                return_value=128_000,
            ),
            patch("api.main.MODEL_CATALOG", {"openai": {"gpt-4.1-mini": {}}}),
        ):
            with pytest.raises(HTTPException) as exc_info:
                fn(_messages(), "openai", "gpt-4.1-mini")
        assert exc_info.value.status_code == 413
        assert exc_info.value.detail["error"] == "input_too_long"
        assert exc_info.value.detail["model_limit"] == 128_000

    def test_raises_413_for_api_input_limit(self):
        """Raises HTTPException 413 mentioning api_limit when api_max_input is set."""
        fn = self._import_helper()
        model_info = {"api_max_input": 32_000}
        with (
            patch(
                "stratifyai.utils.token_counter.count_tokens_for_messages",
                return_value=50_000,
            ),
            patch(
                "stratifyai.utils.token_counter.get_context_window",
                return_value=128_000,
            ),
            patch(
                "api.main.MODEL_CATALOG",
                {"openai": {"gpt-4.1-mini": model_info}},
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                fn(_messages(), "openai", "gpt-4.1-mini")
        detail = exc_info.value.detail
        assert exc_info.value.status_code == 413
        assert detail["error"] == "input_too_long"
        assert detail["api_limit"] == 32_000

    def test_detail_contains_provider_and_model(self):
        """Error details always include provider and model for client diagnostics."""
        fn = self._import_helper()
        with (
            patch(
                "stratifyai.utils.token_counter.count_tokens_for_messages",
                return_value=2_000_000,
            ),
            patch(
                "stratifyai.utils.token_counter.get_context_window",
                return_value=1_000_000,
            ),
            patch(
                "api.main.MODEL_CATALOG", {"anthropic": {"claude-3-haiku-20240307": {}}}
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                fn(_messages(), "anthropic", "claude-3-haiku-20240307")
        assert exc_info.value.detail["provider"] == "anthropic"
        assert exc_info.value.detail["model"] == "claude-3-haiku-20240307"


# ---------------------------------------------------------------------------
# P1 — ResponseCache per-entry TTL
# ---------------------------------------------------------------------------


class TestResponseCachePerEntryTTL:
    """Verify that per-entry TTL overrides the global cache TTL."""

    def test_short_ttl_entry_expires_before_global(self):
        """An entry stored with ttl=1 expires even when global TTL is 3600."""
        cache = ResponseCache(ttl=3600)
        resp = _make_response()
        cache.set("key1", resp, ttl=1)

        # Should be present immediately
        assert cache.get("key1") is not None

        # After 1.1 seconds the short-TTL entry should be gone
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_long_ttl_entry_survives_global_eviction(self):
        """An entry stored with a large ttl is not evicted by a short global TTL."""
        cache = ResponseCache(ttl=1)  # global TTL = 1s
        resp = _make_response()
        cache.set("key_long", resp, ttl=3600)

        time.sleep(1.5)
        # Despite global TTL=1, this entry has its own ttl=3600 and must survive
        assert cache.get("key_long") is not None

    def test_no_override_uses_global_ttl(self):
        """When no per-entry TTL is given the global TTL applies."""
        cache = ResponseCache(ttl=1)
        resp = _make_response()
        cache.set("key_default", resp)
        assert cache.get("key_default") is not None
        time.sleep(1.2)
        assert cache.get("key_default") is None

    def test_get_entries_reports_per_entry_ttl(self):
        """get_entries expires_in should reflect the per-entry TTL, not global."""
        cache = ResponseCache(ttl=3600)
        resp = _make_response()
        cache.set("key_short", resp, ttl=60)

        entries = cache.get_entries()
        assert len(entries) == 1
        # expires_in must be ≤ 60 (well within the 3600 global TTL)
        assert entries[0]["expires_in"] <= 60

    def test_two_entries_independent_ttls(self):
        """Two entries with different TTLs expire independently."""
        cache = ResponseCache(ttl=3600)
        cache.set("fast", _make_response("fast"), ttl=1)
        cache.set("slow", _make_response("slow"), ttl=3600)

        time.sleep(1.2)
        assert cache.get("fast") is None  # expired
        assert cache.get("slow") is not None  # still alive


# ---------------------------------------------------------------------------
# P1 — PersistentResponseCache per-entry TTL
# ---------------------------------------------------------------------------


class TestPersistentCachePerEntryTTL:
    """Verify per-entry TTL on the SQLite backend."""

    def test_short_ttl_expires(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "c.db"), ttl=3600)
        cache.set("k1", _make_response(), ttl=1)
        assert cache.get("k1") is not None
        time.sleep(1.2)
        assert cache.get("k1") is None

    def test_long_ttl_survives_global(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "c.db"), ttl=1)
        cache.set("k2", _make_response(), ttl=3600)
        time.sleep(1.5)
        assert cache.get("k2") is not None

    def test_no_override_uses_global_ttl(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "c.db"), ttl=1)
        cache.set("k3", _make_response())
        assert cache.get("k3") is not None
        time.sleep(1.2)
        assert cache.get("k3") is None

    def test_schema_migration_idempotent(self, tmp_path: Path):
        """Opening the cache twice does not fail (ALTER TABLE is guarded)."""
        db = str(tmp_path / "c.db")
        c1 = PersistentResponseCache(db_path=db)
        c1.set("k", _make_response())
        # Second instance triggers _init_db again — migration column already exists
        c2 = PersistentResponseCache(db_path=db)
        assert c2.get("k") is not None

    def test_get_entries_reflects_per_entry_ttl(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "c.db"), ttl=3600)
        cache.set("k", _make_response(), ttl=120)
        entries = cache.get_entries()
        assert len(entries) == 1
        assert entries[0]["expires_in"] <= 120


# ---------------------------------------------------------------------------
# P1 — cache_response decorator forwards ttl
# ---------------------------------------------------------------------------


class TestCacheResponseDecoratorTTL:
    """Verify the decorator passes its ttl through to ResponseCache.set()."""

    @pytest.mark.asyncio
    async def test_decorator_stores_with_custom_ttl(self):
        """cache_response(ttl=30) stores entries with ttl=30 (not global 3600)."""
        from stratifyai.models import ChatRequest  # noqa: PLC0415

        custom_cache = ResponseCache(ttl=3600)

        @cache_response(ttl=30, cache_instance=custom_cache)
        async def fake_chat(request: ChatRequest) -> ChatResponse:
            return _make_response()

        # Use the real ChatRequest to exercise the decorator
        req = ChatRequest(
            model="gpt-4.1-mini",
            messages=_messages(),
            temperature=0.7,
            max_tokens=100,
        )

        original_set = custom_cache.set
        recorded_ttl: list[int | None] = []

        def capturing_set(key, response, ttl=None):
            recorded_ttl.append(ttl)
            return original_set(key, response, ttl=ttl)

        custom_cache.set = capturing_set  # type: ignore[method-assign]

        await fake_chat(req)
        assert len(recorded_ttl) == 1
        assert recorded_ttl[0] == 30

    @pytest.mark.asyncio
    async def test_decorator_short_ttl_entry_expires(self):
        """Entry added via @cache_response(ttl=1) expires after 1 second."""
        custom_cache = ResponseCache(ttl=3600)

        from stratifyai.models import ChatRequest  # noqa: PLC0415

        @cache_response(ttl=1, cache_instance=custom_cache)
        async def fake_chat(req: ChatRequest) -> ChatResponse:
            return _make_response()

        req = ChatRequest(
            model="gpt-4.1-mini",
            messages=_messages(),
            temperature=0.7,
            max_tokens=100,
        )
        await fake_chat(req)
        from stratifyai.caching import generate_cache_key  # noqa: PLC0415

        key = generate_cache_key(
            model=req.model,
            messages=req.messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        assert custom_cache.get(key) is not None
        time.sleep(1.2)
        assert custom_cache.get(key) is None
