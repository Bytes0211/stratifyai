"""Tests for caching functionality."""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.caching import (
    ResponseCache,
    cache_response,
    clear_cache,
    generate_cache_key,
    get_cache_stats,
)
from stratifyai.models import ChatResponse, Message, Usage


class TestCacheKey:
    """Tests for cache key generation."""

    def test_generate_cache_key_basic(self):
        """Test basic cache key generation."""
        messages = [Message(role="user", content="Hello")]
        key = generate_cache_key(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
        )
        assert isinstance(key, str)
        assert len(key) == 64  # SHA256 hash length

    def test_generate_cache_key_same_params_same_key(self):
        """Test that same parameters generate same key."""
        messages = [Message(role="user", content="Hello")]
        key1 = generate_cache_key(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
        )
        key2 = generate_cache_key(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
        )
        assert key1 == key2

    def test_generate_cache_key_different_params_different_key(self):
        """Test that different parameters generate different keys."""
        messages = [Message(role="user", content="Hello")]
        key1 = generate_cache_key(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
        )
        key2 = generate_cache_key(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.8,
        )
        assert key1 != key2

    def test_generate_cache_key_with_max_tokens(self):
        """Test cache key generation with max_tokens."""
        messages = [Message(role="user", content="Hello")]
        key1 = generate_cache_key(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=100,
        )
        key2 = generate_cache_key(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=200,
        )
        assert key1 != key2

    def test_generate_cache_key_ignores_stream(self):
        """Test that stream parameter doesn't affect cache key."""
        messages = [Message(role="user", content="Hello")]
        key1 = generate_cache_key(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
            stream=False,
        )
        key2 = generate_cache_key(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.7,
            stream=True,
        )
        assert key1 == key2


class TestResponseCache:
    """Tests for ResponseCache class."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = ResponseCache(ttl=3600, max_size=100)
        assert cache.ttl == 3600
        assert cache.max_size == 100

    def test_cache_set_and_get(self):
        """Test setting and getting cache entries."""
        cache = ResponseCache()
        response = ChatResponse(
            id="test-1",
            model="gpt-4.1-mini",
            content="Hello!",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
        )

        cache.set("test-key", response)
        cached = cache.get("test-key")

        assert cached is not None
        assert cached.id == "test-1"
        assert cached.content == "Hello!"

    def test_cache_miss(self):
        """Test cache miss."""
        cache = ResponseCache()
        cached = cache.get("nonexistent-key")
        assert cached is None

    def test_cache_expiration(self):
        """Test cache entry expiration."""
        cache = ResponseCache(ttl=1)  # 1 second TTL
        response = ChatResponse(
            id="test-1",
            model="gpt-4.1-mini",
            content="Hello!",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
        )

        cache.set("test-key", response)
        
        # Should be cached immediately
        assert cache.get("test-key") is not None
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should be expired
        assert cache.get("test-key") is None

    def test_cache_max_size(self):
        """Test cache max size eviction."""
        cache = ResponseCache(max_size=2)
        
        for i in range(3):
            response = ChatResponse(
                id=f"test-{i}",
                model="gpt-4.1-mini",
                content=f"Response {i}",
                finish_reason="stop",
                usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                provider="openai",
                created_at=datetime.now(),
                raw_response={},
            )
            cache.set(f"key-{i}", response)
            time.sleep(0.01)  # Ensure different timestamps

        # First entry should be evicted
        assert cache.get("key-0") is None
        assert cache.get("key-1") is not None
        assert cache.get("key-2") is not None

    def test_cache_hit_count(self):
        """Test cache hit counting."""
        cache = ResponseCache()
        response = ChatResponse(
            id="test-1",
            model="gpt-4.1-mini",
            content="Hello!",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
        )

        cache.set("test-key", response)
        
        # Access multiple times
        cache.get("test-key")
        cache.get("test-key")
        cache.get("test-key")
        
        stats = cache.get_stats()
        assert stats["total_hits"] == 3

    def test_cache_clear(self):
        """Test cache clearing."""
        cache = ResponseCache()
        response = ChatResponse(
            id="test-1",
            model="gpt-4.1-mini",
            content="Hello!",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
        )

        cache.set("test-key", response)
        assert cache.get("test-key") is not None
        
        cache.clear()
        assert cache.get("test-key") is None
        assert cache.get_stats()["size"] == 0

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = ResponseCache(ttl=3600, max_size=1000)
        stats = cache.get_stats()
        
        assert stats["size"] == 0
        assert stats["max_size"] == 1000
        assert stats["ttl"] == 3600
        assert stats["total_hits"] == 0


class TestCacheDecorator:
    """Tests for cache_response decorator."""

    @pytest.mark.asyncio
    async def test_decorator_caches_response(self):
        """Test that decorator caches responses."""
        cache = ResponseCache()
        call_count = 0

        @cache_response(cache_instance=cache)
        async def mock_api_call(**kwargs):
            nonlocal call_count
            call_count += 1
            return ChatResponse(
                id="test-1",
                model=kwargs["model"],
                content="Hello!",
                finish_reason="stop",
                usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                provider="openai",
                created_at=datetime.now(),
                raw_response={},
            )

        # First call
        response1 = await mock_api_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hi")],
            temperature=0.7,
        )
        assert call_count == 1

        # Second call with same params - should use cache
        response2 = await mock_api_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hi")],
            temperature=0.7,
        )
        assert call_count == 1  # Should not increment
        assert response2.id == response1.id

    @pytest.mark.asyncio
    async def test_decorator_different_params_no_cache(self):
        """Test that different parameters don't use cache."""
        cache = ResponseCache()
        call_count = 0

        @cache_response(cache_instance=cache)
        async def mock_api_call(**kwargs):
            nonlocal call_count
            call_count += 1
            return ChatResponse(
                id=f"test-{call_count}",
                model=kwargs["model"],
                content="Hello!",
                finish_reason="stop",
                usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                provider="openai",
                created_at=datetime.now(),
                raw_response={},
            )

        # First call
        await mock_api_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hi")],
            temperature=0.7,
        )
        assert call_count == 1

        # Second call with different params
        await mock_api_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hi")],
            temperature=0.8,
        )
        assert call_count == 2  # Should increment

    @pytest.mark.asyncio
    async def test_decorator_respects_ttl(self):
        """Test that decorator respects TTL."""
        cache = ResponseCache(ttl=1)
        call_count = 0

        @cache_response(ttl=1, cache_instance=cache)
        async def mock_api_call(**kwargs):
            nonlocal call_count
            call_count += 1
            return ChatResponse(
                id=f"test-{call_count}",
                model=kwargs["model"],
                content="Hello!",
                finish_reason="stop",
                usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
                provider="openai",
                created_at=datetime.now(),
                raw_response={},
            )

        # First call
        await mock_api_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hi")],
            temperature=0.7,
        )
        assert call_count == 1

        # Wait for cache expiration
        await asyncio.sleep(1.1)

        # Should call API again
        await mock_api_call(
            model="gpt-4.1-mini",
            messages=[Message(role="user", content="Hi")],
            temperature=0.7,
        )
        assert call_count == 2


class TestGlobalCacheFunctions:
    """Tests for global cache functions."""

    def test_get_cache_stats(self):
        """Test get_cache_stats function."""
        clear_cache()  # Start fresh
        stats = get_cache_stats()
        assert "size" in stats
        assert "max_size" in stats
        assert "ttl" in stats
        assert "total_hits" in stats

    def test_clear_cache_function(self):
        """Test clear_cache function."""
        # This test just ensures the function works
        # without errors
        clear_cache()
        stats = get_cache_stats()
        assert stats["size"] == 0


class TestCacheCostCalculation:
    """Tests for cache cost calculation in OpenAI provider."""

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    def test_cache_cost_calculation(self, mock_openai_client):
        """Test that cache costs are calculated correctly."""
        from stratifyai.models import Message, Usage
        from stratifyai.providers.openai import OpenAIProvider

        # Mock OpenAI client
        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client

        # Create provider
        provider = OpenAIProvider(api_key="test-key")

        # Test cache cost calculation
        cache_cost = provider._calculate_cache_cost(
            cache_creation_tokens=1000,
            cache_read_tokens=500,
            model="gpt-4.1-mini"
        )

        # gpt-4.1-mini: cache_write=0.1875, cache_read=0.015 per 1M tokens
        # 1000 tokens write: (1000 / 1M) * 0.1875 = 0.0001875
        # 500 tokens read: (500 / 1M) * 0.015 = 0.0000075
        # Total: 0.000195
        expected_cost = (1000 / 1_000_000) * 0.1875 + (500 / 1_000_000) * 0.015
        assert abs(cache_cost - expected_cost) < 0.000001

    @patch("stratifyai.providers.openai.AsyncOpenAI")
    def test_supports_caching(self, mock_openai_client):
        """Test supports_caching method."""
        from stratifyai.providers.openai import OpenAIProvider

        mock_client = MagicMock()
        mock_openai_client.return_value = mock_client

        provider = OpenAIProvider(api_key="test-key")

        # Models with caching support
        assert provider.supports_caching("gpt-4.1-mini") is True
        assert provider.supports_caching("gpt-5") is True

        # Models without caching support
        assert provider.supports_caching("o1") is False
        assert provider.supports_caching("o3-mini") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
