"""Tests for PersistentResponseCache (SQLite backend)."""

import tempfile
import time
from datetime import datetime
from pathlib import Path

import pytest

from stratifyai.caching import PersistentResponseCache
from stratifyai.models import ChatResponse, Usage


def _make_response(content: str = "Hello!", model: str = "gpt-4.1-mini") -> ChatResponse:
    return ChatResponse(
        id="test-1",
        model=model,
        content=content,
        finish_reason="stop",
        usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15, cost_usd=0.001),
        provider="openai",
        created_at=datetime.now(),
        raw_response={"debug": True},
    )


class TestPersistentCacheBasics:
    """Basic get/set/clear operations."""

    def test_set_and_get(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "cache.db"))
        resp = _make_response()
        cache.set("k1", resp)

        cached = cache.get("k1")
        assert cached is not None
        assert cached.content == "Hello!"
        assert cached.model == "gpt-4.1-mini"
        assert cached.usage.cost_usd == pytest.approx(0.001)

    def test_miss_returns_none(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "cache.db"))
        assert cache.get("nonexistent") is None

    def test_clear(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "cache.db"))
        cache.set("k1", _make_response())
        cache.set("k2", _make_response())
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_ttl_expiration(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "cache.db"), ttl=1)
        cache.set("k1", _make_response())

        # Available immediately
        assert cache.get("k1") is not None

        time.sleep(1.1)

        # Expired
        assert cache.get("k1") is None


class TestPersistentCachePersistence:
    """Data survives across instances (the whole point)."""

    def test_survives_restart(self, tmp_path: Path):
        db = str(tmp_path / "cache.db")

        # Instance 1: write
        cache1 = PersistentResponseCache(db_path=db, ttl=3600)
        cache1.set("k1", _make_response("answer1"))
        del cache1

        # Instance 2: read
        cache2 = PersistentResponseCache(db_path=db, ttl=3600)
        cached = cache2.get("k1")
        assert cached is not None
        assert cached.content == "answer1"


class TestPersistentCacheEviction:
    """Max-size eviction."""

    def test_evicts_oldest(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "cache.db"), max_size=2)
        cache.set("k0", _make_response("r0"))
        time.sleep(0.01)
        cache.set("k1", _make_response("r1"))
        time.sleep(0.01)
        cache.set("k2", _make_response("r2"))  # should evict k0

        assert cache.get("k0") is None
        assert cache.get("k1") is not None
        assert cache.get("k2") is not None


class TestPersistentCacheStats:
    """get_stats / get_entries."""

    def test_stats(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "cache.db"))
        cache.set("k1", _make_response())
        cache.get("k1")
        cache.get("k1")

        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["total_hits"] == 2
        assert stats["backend"] == "sqlite"

    def test_get_entries(self, tmp_path: Path):
        cache = PersistentResponseCache(db_path=str(tmp_path / "cache.db"))
        cache.set("k1", _make_response())
        cache.get("k1")

        entries = cache.get_entries()
        assert len(entries) == 1
        assert entries[0]["hits"] == 1
        assert entries[0]["model"] == "gpt-4.1-mini"
