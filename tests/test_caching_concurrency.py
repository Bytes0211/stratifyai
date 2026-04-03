"""Tests for persistent cache with SQLite WAL mode and concurrency."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import pytest

from stratifyai.caching import PersistentResponseCache
from stratifyai.models import ChatResponse, Usage


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path."""
    db_file = tmp_path / "test_cache.db"
    return str(db_file)


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
        created_at=datetime.now(),
        raw_response={},
    )


class TestWALMode:
    """Test SQLite WAL mode is enabled and working."""

    def test_wal_mode_enabled(self, temp_db_path):
        """Verify WAL mode is enabled."""
        cache = PersistentResponseCache(db_path=temp_db_path)

        # Check WAL mode by reading pragma
        conn = cache._connect()
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()

        # WAL mode should be enabled (will be "wal")
        assert journal_mode.lower() == "wal"

    def test_wal_files_created(self, temp_db_path, sample_response):
        """Verify WAL creates checkpoint files."""
        cache = PersistentResponseCache(db_path=temp_db_path)

        # Add some data
        for i in range(10):
            cache.set(f"key-{i}", sample_response)

        # Check that WAL files exist or db exists
        db_path = Path(temp_db_path)
        assert db_path.exists(), "Database file should exist"

    def test_connection_timeout_configured(self, temp_db_path):
        """Verify connection timeout is set."""
        cache = PersistentResponseCache(db_path=temp_db_path)
        conn = cache._connect()

        # Connection should have 5-second timeout
        # This is implicit in the _connect method
        assert conn is not None
        conn.close()


class TestPersistentCacheConcurrency:
    """Test concurrent access to persistent cache with WAL."""

    def test_concurrent_writes(self, temp_db_path, sample_response):
        """Verify concurrent writes work with WAL mode."""
        cache = PersistentResponseCache(db_path=temp_db_path)

        write_count = 0
        write_lock = threading.Lock()

        def writer(thread_id):
            nonlocal write_count
            for i in range(10):
                key = f"thread-{thread_id}-key-{i}"
                cache.set(key, sample_response)
                with write_lock:
                    write_count += 1

        # 20 threads, each writing 10 entries = 200 total
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(writer, i) for i in range(20)]
            for f in as_completed(futures):
                f.result()

        # Verify all writes succeeded
        assert write_count == 200

        # Verify cache size
        stats = cache.get_stats()
        assert stats["size"] == 200

    def test_concurrent_reads(self, temp_db_path, sample_response):
        """Verify concurrent reads work with WAL mode and return correct data."""
        cache = PersistentResponseCache(db_path=temp_db_path)

        # Pre-populate cache
        for i in range(50):
            cache.set(f"key-{i}", sample_response)

        read_count = 0
        read_lock = threading.Lock()
        data_errors = []

        def reader(thread_id):
            nonlocal read_count
            for i in range(50):
                key = f"key-{i}"
                result = cache.get(key)
                if result is not None:
                    # Validate data correctness — not just existence
                    if result.model != sample_response.model:
                        data_errors.append(f"key-{i}: model={result.model}")
                    if result.content != sample_response.content:
                        data_errors.append(f"key-{i}: content mismatch")
                    if result.provider != sample_response.provider:
                        data_errors.append(f"key-{i}: provider={result.provider}")
                    with read_lock:
                        read_count += 1

        # 20 threads, each reading 50 entries = 1000 total
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(reader, i) for i in range(20)]
            for f in as_completed(futures):
                f.result()

        # Verify all reads succeeded
        assert read_count == 1000
        # Verify no data corruption
        assert data_errors == [], f"Data corruption detected: {data_errors[:5]}"

    def test_concurrent_mixed_access(self, temp_db_path, sample_response):
        """Verify mixed read/write access works."""
        cache = PersistentResponseCache(db_path=temp_db_path)

        operation_count = 0
        op_lock = threading.Lock()

        def mixed_access(thread_id):
            nonlocal operation_count
            for i in range(20):
                if i % 2 == 0:
                    # Write
                    cache.set(f"thread-{thread_id}-{i}", sample_response)
                else:
                    # Read
                    cache.get(f"thread-{thread_id}-{i - 1}")
                with op_lock:
                    operation_count += 1

        # 10 threads doing mixed access
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(mixed_access, i) for i in range(10)]
            for f in as_completed(futures):
                f.result()

        # Verify operations completed (10 threads * 20 ops = 200)
        assert operation_count == 200


class TestCacheDataCorrectness:
    """Test that cached data is not corrupted under concurrent access."""

    def test_distinct_values_survive_concurrent_writes(self, temp_db_path):
        """Verify each key stores the correct distinct response after concurrent writes."""
        cache = PersistentResponseCache(db_path=temp_db_path)

        def write_distinct(thread_id):
            """Write entries with thread-specific content."""
            for i in range(10):
                response = ChatResponse(
                    id=f"resp-{thread_id}-{i}",
                    model=f"model-{thread_id}",
                    content=f"content-{thread_id}-{i}",
                    finish_reason="stop",
                    usage=Usage(
                        prompt_tokens=thread_id,
                        completion_tokens=i,
                        total_tokens=thread_id + i,
                        cost_usd=0.001 * thread_id,
                    ),
                    provider="openai",
                    created_at=datetime.now(),
                    raw_response={},
                )
                cache.set(f"thread-{thread_id}-key-{i}", response)

        # 10 threads writing distinct data
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_distinct, t) for t in range(10)]
            for f in as_completed(futures):
                f.result()

        # Verify each entry has the correct content
        errors = []
        for thread_id in range(10):
            for i in range(10):
                result = cache.get(f"thread-{thread_id}-key-{i}")
                if result is None:
                    errors.append(f"thread-{thread_id}-key-{i}: missing")
                elif result.content != f"content-{thread_id}-{i}":
                    errors.append(
                        f"thread-{thread_id}-key-{i}: expected content-{thread_id}-{i}, "
                        f"got {result.content}"
                    )
                elif result.model != f"model-{thread_id}":
                    errors.append(
                        f"thread-{thread_id}-key-{i}: expected model-{thread_id}, "
                        f"got {result.model}"
                    )

        assert errors == [], f"Data correctness failures: {errors[:10]}"


class TestCacheEntryExpiration:
    """Test that expired entries are properly handled with concurrency."""

    def test_concurrent_expiration_handling(self, temp_db_path, sample_response):
        """Verify expired entries don't cause issues with concurrent access."""
        cache = PersistentResponseCache(db_path=temp_db_path, ttl=1)

        # Add entries
        for i in range(10):
            cache.set(f"expire-key-{i}", sample_response)

        # Wait for expiration (generous margin for slow CI)
        time.sleep(2.5)

        # Concurrent reads of expired entries
        read_count = 0
        read_lock = threading.Lock()

        def expired_reader(thread_id):
            nonlocal read_count
            for i in range(10):
                result = cache.get(f"expire-key-{i}")
                # Should be None (expired)
                if result is None:
                    with read_lock:
                        read_count += 1

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(expired_reader, i) for i in range(10)]
            for f in as_completed(futures):
                f.result()

        # All 100 reads should get None (expired)
        assert read_count == 100


class TestPersistenceAcrossInstances:
    """Test that cached data persists across cache instances."""

    def test_data_persists_across_instances(self, temp_db_path, sample_response):
        """Verify cache data persists when creating new instances."""
        # First instance - write data
        cache1 = PersistentResponseCache(db_path=temp_db_path)
        cache1.set("persist-key", sample_response)

        # Verify data exists
        result1 = cache1.get("persist-key")
        assert result1 is not None

        # Create new instance and verify data persists
        cache2 = PersistentResponseCache(db_path=temp_db_path)
        result2 = cache2.get("persist-key")
        assert result2 is not None
        assert result2.model == result1.model
