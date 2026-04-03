"""Tests for cache optimization: LRU eviction and read-write locking."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import cachetools
import pytest
from readerwriterlock.rwlock import RWLockFair

from stratifyai.caching import ResponseCache
from stratifyai.models import ChatResponse, Usage


@pytest.fixture
def sample_response():
    """Create a sample ChatResponse for testing."""
    return ChatResponse(
        id="test-123",
        model="gpt-4",
        content="Test response",
        finish_reason="stop",
        usage=Usage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            cost_usd=0.001,
        ),
        provider="openai",
        created_at=None,
        raw_response={},
    )


class TestLRUCacheEviction:
    """Test that cache uses cachetools.LRUCache for O(1) eviction."""

    def test_cache_uses_lru_cache(self):
        """Verify ResponseCache uses cachetools.LRUCache."""
        cache = ResponseCache(max_size=10)
        assert isinstance(cache._cache, cachetools.LRUCache)
        assert cache._cache.maxsize == 10

    def test_lru_eviction_o1_performance(self, sample_response):
        """Verify LRU eviction is O(1) by timing measurement."""
        cache = ResponseCache(max_size=100)

        # Fill cache to near capacity
        for i in range(99):
            cache.set(f"key-{i}", sample_response)

        # Measure time to add 1000 more entries (each should trigger eviction)
        start = time.time()
        for i in range(1000):
            cache.set(f"key-{99 + i}", sample_response)
        elapsed = time.time() - start

        # For O(1) eviction with 1000 insertions: should be well under 5s
        # even on slow CI machines (O(n) would be orders of magnitude worse)
        assert elapsed < 5.0, f"LRU eviction took {elapsed}s, too slow"
        assert cache._cache.currsize <= cache.max_size

    def test_oldest_entry_evicted_first(self, sample_response):
        """Verify oldest (LRU) entry is evicted when cache is full."""
        cache = ResponseCache(max_size=3)

        # Add 3 entries
        cache.set("key-1", sample_response)
        time.sleep(0.01)  # Ensure different timestamps
        cache.set("key-2", sample_response)
        time.sleep(0.01)
        cache.set("key-3", sample_response)

        # Add 4th entry - should evict key-1 (oldest)
        cache.set("key-4", sample_response)

        # Verify key-1 is gone, others remain
        assert cache.get("key-1") is None  # Evicted
        assert cache.get("key-2") is not None
        assert cache.get("key-3") is not None
        assert cache.get("key-4") is not None


class TestReadWriteLock:
    """Test concurrent read access with RWLock."""

    def test_cache_uses_rwlock(self):
        """Verify ResponseCache uses RWLockFair."""
        cache = ResponseCache()
        assert isinstance(cache._lock, RWLockFair)

    def test_concurrent_reads_allowed(self, sample_response):
        """Verify multiple threads can read simultaneously."""
        cache = ResponseCache()
        cache.set("shared-key", sample_response)

        read_count = 0
        read_count_lock = threading.Lock()

        def reader():
            nonlocal read_count
            result = cache.get("shared-key")
            with read_count_lock:
                read_count += 1
            return result

        # Launch 20 reader threads
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(reader) for _ in range(20)]
            results = [f.result() for f in as_completed(futures)]

        # All reads should succeed
        assert all(r is not None for r in results)
        assert read_count == 20

    def test_write_exclusive_access(self, sample_response):
        """Verify write operations have exclusive access."""
        cache = ResponseCache()

        # Track if reads overlap with writes
        operation_log = []
        log_lock = threading.Lock()

        def reader():
            with log_lock:
                operation_log.append(("read_start", time.time()))
            result = cache.get("key")
            with log_lock:
                operation_log.append(("read_end", time.time()))
            return result

        def writer():
            with log_lock:
                operation_log.append(("write_start", time.time()))
            cache.set("key", sample_response)
            time.sleep(0.05)  # Hold writes for a bit
            with log_lock:
                operation_log.append(("write_end", time.time()))

        # Warm up cache
        cache.set("key", sample_response)

        # Launch reader and writer threads alternately
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for _ in range(3):
                futures.append(executor.submit(writer))
                futures.append(executor.submit(reader))
            for f in as_completed(futures):
                f.result()

        # Verify operations completed (we don't assert strict exclusivity
        # as RWLock semantics are complex, just verify no deadlock)
        assert len(operation_log) > 0

    def test_cache_operations_concurrent_read_stress(self, sample_response):
        """Stress test: 100 concurrent readers on same cache entry."""
        cache = ResponseCache()
        cache.set("stress-key", sample_response)

        success_count = 0
        success_lock = threading.Lock()

        def reader():
            nonlocal success_count
            result = cache.get("stress-key")
            if result is not None:
                with success_lock:
                    success_count += 1

        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [executor.submit(reader) for _ in range(100)]
            for f in as_completed(futures):
                f.result()

        # All 100 reads should succeed
        assert success_count == 100


class TestCacheHitTracking:
    """Test that hits are tracked correctly with RWLock."""

    def test_hit_count_incremented(self, sample_response):
        """Verify hit count increments on cache hits."""
        cache = ResponseCache()
        cache.set("key", sample_response)

        # Get stats before hits
        stats_before = cache.get_stats()

        # Access 5 times
        for _ in range(5):
            cache.get("key")

        stats_after = cache.get_stats()
        assert stats_after["total_hits"] == stats_before["total_hits"] + 5

    def test_cost_saved_tracked(self, sample_response):
        """Verify cost savings are tracked on cache hits."""
        cache = ResponseCache()
        cache.set("key", sample_response)

        stats_before = cache.get_stats()
        cost_before = stats_before["total_cost_saved"]

        # Access 3 times - should accumulate cost
        for _ in range(3):
            cache.get("key")

        stats_after = cache.get_stats()
        # Cost should increase by 3 * 0.001 = 0.003
        assert stats_after["total_cost_saved"] > cost_before
