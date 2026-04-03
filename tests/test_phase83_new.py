"""Tests for Phase 8.3 new features: provider pooling & ChatResponse.to_dict."""

from datetime import datetime
from unittest.mock import patch

import pytest

from stratifyai.client import LLMClient, _provider_pool, close_all_providers
from stratifyai.models import ChatResponse, Usage

# ---------- 8.3.7 Provider connection pooling ----------


class TestProviderPool:
    """Tests for module-level provider pool and close helpers."""

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    def test_pool_reuses_provider(self, mock_openai):
        """Two LLMClients with the same key share one pooled provider."""
        c1 = LLMClient(provider="openai", api_key="key-a")
        c2 = LLMClient(provider="openai", api_key="key-a")
        assert c1._providers["openai"] is c2._providers["openai"]
        assert len(_provider_pool) == 1

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    def test_pool_separates_different_keys(self, mock_openai):
        """Different API keys yield separate providers."""
        c1 = LLMClient(provider="openai", api_key="key-a")
        c2 = LLMClient(provider="openai", api_key="key-b")
        assert c1._providers["openai"] is not c2._providers["openai"]
        assert len(_provider_pool) == 2

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    def test_close_removes_from_pool(self, mock_openai):
        """client.close() removes the provider from the pool."""
        c = LLMClient(provider="openai", api_key="key-a")
        assert len(_provider_pool) == 1
        c.close()
        assert len(_provider_pool) == 0
        assert c._providers == {}

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    def test_close_all_providers(self, mock_openai):
        """close_all_providers() empties the pool."""
        LLMClient(provider="openai", api_key="key-a")
        LLMClient(provider="openai", api_key="key-b")
        assert len(_provider_pool) == 2
        close_all_providers()
        assert len(_provider_pool) == 0

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    @pytest.mark.asyncio
    async def test_async_context_manager(self, mock_openai):
        """LLMClient can be used as async context manager."""
        async with LLMClient(provider="openai", api_key="key-a"):
            assert len(_provider_pool) == 1
        # After exiting context, pool entry removed
        assert len(_provider_pool) == 0


# ---------- 8.3.8 ChatResponse.to_dict ----------


class TestChatResponseToDict:
    """Tests for ChatResponse.to_dict serialization."""

    def _make_response(self) -> ChatResponse:
        return ChatResponse(
            id="resp-1",
            model="gpt-4.1-mini",
            content="Hello",
            finish_reason="stop",
            usage=Usage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15, cost_usd=0.001
            ),
            provider="openai",
            created_at=datetime(2025, 1, 1, 12, 0, 0),
            raw_response={"raw": True},
            latency_ms=42.5,
        )

    def test_excludes_raw_response_by_default(self):
        d = self._make_response().to_dict()
        assert "raw_response" not in d
        assert d["content"] == "Hello"
        assert d["latency_ms"] == 42.5

    def test_includes_raw_response_when_requested(self):
        d = self._make_response().to_dict(include_raw=True)
        assert d["raw_response"] == {"raw": True}

    def test_datetime_serialized_as_iso(self):
        d = self._make_response().to_dict()
        assert d["created_at"] == "2025-01-01T12:00:00"

    def test_usage_nested(self):
        d = self._make_response().to_dict()
        assert d["usage"]["prompt_tokens"] == 10
        assert d["usage"]["cost_usd"] == 0.001
