"""Unit tests for Phase 7.4: Enhanced Caching UI."""

import pytest
import time
from stratifyai.caching import ResponseCache, CacheEntry, get_cache_stats, get_cache_entries, clear_cache
from stratifyai.models import ChatResponse, Usage
from datetime import datetime


class TestEnhancedCaching:
    """Test enhanced caching functionality."""
    
    def test_cache_miss_tracking(self):
        """Test that cache misses are tracked correctly."""
        cache = ResponseCache(ttl=60)
        
        # Initial state
        stats = cache.get_stats()
        assert stats['total_misses'] == 0
        
        # Miss on get
        result = cache.get("nonexistent_key")
        assert result is None
        
        stats = cache.get_stats()
        assert stats['total_misses'] == 1
        
        # Another miss
        cache.get("another_key")
        stats = cache.get_stats()
        assert stats['total_misses'] == 2
    
    def test_cache_hit_tracking(self):
        """Test that cache hits are tracked correctly."""
        cache = ResponseCache(ttl=60)
        
        # Create mock response
        response = ChatResponse(
            id="test-123",
            model="gpt-4o",
            content="Test response",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30, cost_usd=0.001),
            provider="openai",
            created_at=datetime.now(),
            raw_response={}
        )
        
        # Cache the response
        cache.set("test_key", response)
        
        # Hit the cache
        cached = cache.get("test_key")
        assert cached is not None
        assert cached.content == "Test response"
        
        stats = cache.get_stats()
        assert stats['total_hits'] == 1
        assert stats['total_misses'] == 0
        
        # Hit again
        cache.get("test_key")
        stats = cache.get_stats()
        assert stats['total_hits'] == 2
    
    def test_cost_savings_tracking(self):
        """Test that cost savings are tracked correctly."""
        cache = ResponseCache(ttl=60)
        
        # Create response with cost
        response = ChatResponse(
            id="test-123",
            model="gpt-4o",
            content="Test",
            finish_reason="stop",
            usage=Usage(prompt_tokens=100, completion_tokens=200, total_tokens=300, cost_usd=0.005),
            provider="openai",
            created_at=datetime.now(),
            raw_response={}
        )
        
        cache.set("key1", response)
        
        # First hit
        cache.get("key1")
        stats = cache.get_stats()
        assert stats['total_cost_saved'] == 0.005
        
        # Second hit
        cache.get("key1")
        stats = cache.get_stats()
        assert stats['total_cost_saved'] == 0.010
        
        # Third hit
        cache.get("key1")
        stats = cache.get_stats()
        assert abs(stats['total_cost_saved'] - 0.015) < 0.0001
    
    def test_hit_rate_calculation(self):
        """Test that hit rate is calculated correctly."""
        cache = ResponseCache(ttl=60)
        
        response = ChatResponse(
            id="test-123",
            model="gpt-4o",
            content="Test",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            provider="openai",
            created_at=datetime.now(),
            raw_response={}
        )
        
        cache.set("key1", response)
        
        # 1 hit, 0 misses - 100%
        cache.get("key1")
        stats = cache.get_stats()
        assert stats['hit_rate'] == 100.0
        
        # 1 hit, 1 miss - 50%
        cache.get("nonexistent")
        stats = cache.get_stats()
        assert stats['hit_rate'] == 50.0
        
        # 2 hits, 1 miss - 66.7%
        cache.get("key1")
        stats = cache.get_stats()
        assert abs(stats['hit_rate'] - 66.67) < 0.1
    
    def test_cache_entry_details(self):
        """Test getting detailed cache entry information."""
        cache = ResponseCache(ttl=60)
        
        response1 = ChatResponse(
            id="test-1",
            model="gpt-4o",
            content="Response 1",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30, cost_usd=0.001),
            provider="openai",
            created_at=datetime.now(),
            raw_response={}
        )
        
        response2 = ChatResponse(
            id="test-2",
            model="claude-3-5-sonnet-20241022",
            content="Response 2",
            finish_reason="stop",
            usage=Usage(prompt_tokens=15, completion_tokens=25, total_tokens=40, cost_usd=0.002),
            provider="anthropic",
            created_at=datetime.now(),
            raw_response={}
        )
        
        cache.set("key1", response1)
        cache.set("key2", response2)
        
        # Hit key1 twice, key2 once
        cache.get("key1")
        cache.get("key1")
        cache.get("key2")
        
        entries = cache.get_entries()
        
        assert len(entries) == 2
        
        # Entries should be sorted by hits (key1 first with 2 hits)
        assert entries[0]['hits'] == 2
        assert entries[0]['model'] == "gpt-4o"
        assert entries[0]['provider'] == "openai"
        assert entries[0]['cost_saved'] == 0.002
        
        assert entries[1]['hits'] == 1
        assert entries[1]['model'] == "claude-3-5-sonnet-20241022"
        assert entries[1]['provider'] == "anthropic"
        assert entries[1]['cost_saved'] == 0.002
    
    def test_cache_expiration(self):
        """Test that expired entries are counted as misses."""
        cache = ResponseCache(ttl=1)  # 1 second TTL
        
        response = ChatResponse(
            id="test-123",
            model="gpt-4o",
            content="Test",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            provider="openai",
            created_at=datetime.now(),
            raw_response={}
        )
        
        cache.set("key1", response)
        
        # Immediate get should hit
        result = cache.get("key1")
        assert result is not None
        
        stats = cache.get_stats()
        assert stats['total_hits'] == 1
        assert stats['total_misses'] == 0
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Get after expiration should miss
        result = cache.get("key1")
        assert result is None
        
        stats = cache.get_stats()
        # After expiration, entry is deleted so total_hits resets to 0
        assert stats['total_hits'] == 0
        assert stats['total_misses'] == 1
        assert stats['size'] == 0  # Entry should be removed
    
    def test_cache_clear_resets_stats(self):
        """Test that clearing cache resets all statistics."""
        cache = ResponseCache(ttl=60)
        
        response = ChatResponse(
            id="test-123",
            model="gpt-4o",
            content="Test",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30, cost_usd=0.005),
            provider="openai",
            created_at=datetime.now(),
            raw_response={}
        )
        
        cache.set("key1", response)
        cache.get("key1")
        cache.get("nonexistent")
        
        stats = cache.get_stats()
        assert stats['size'] > 0
        assert stats['total_hits'] > 0
        assert stats['total_misses'] > 0
        assert stats['total_cost_saved'] > 0
        
        # Clear cache
        cache.clear()
        
        stats = cache.get_stats()
        assert stats['size'] == 0
        assert stats['total_hits'] == 0
        assert stats['total_misses'] == 0
        assert stats['total_cost_saved'] == 0.0
    
    def test_cache_entry_age_and_expiry(self):
        """Test that entry age and expiry time are calculated correctly."""
        cache = ResponseCache(ttl=100)
        
        response = ChatResponse(
            id="test-123",
            model="gpt-4o",
            content="Test",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            provider="openai",
            created_at=datetime.now(),
            raw_response={}
        )
        
        cache.set("key1", response)
        
        # Small delay
        time.sleep(0.1)
        
        entries = cache.get_entries()
        assert len(entries) == 1
        
        entry = entries[0]
        assert entry['age_seconds'] >= 0
        assert entry['expires_in'] <= 100
        assert entry['expires_in'] < 100  # Should be slightly less due to time passed
    
    def test_global_cache_functions(self):
        """Test global cache helper functions."""
        # Clear any existing state
        clear_cache()
        
        stats = get_cache_stats()
        assert stats['size'] == 0
        
        entries = get_cache_entries()
        assert len(entries) == 0
    
    def test_multiple_entries_cost_tracking(self):
        """Test cost tracking with multiple entries."""
        cache = ResponseCache(ttl=60)
        
        # Create 3 responses with different costs
        for i in range(3):
            response = ChatResponse(
                id=f"test-{i}",
                model="gpt-4o",
                content=f"Response {i}",
                finish_reason="stop",
                usage=Usage(
                    prompt_tokens=10 * (i + 1),
                    completion_tokens=20 * (i + 1),
                    total_tokens=30 * (i + 1),
                    cost_usd=0.001 * (i + 1)
                ),
                provider="openai",
                created_at=datetime.now(),
                raw_response={}
            )
            cache.set(f"key{i}", response)
        
        # Hit each entry once
        cache.get("key0")  # Saves $0.001
        cache.get("key1")  # Saves $0.002
        cache.get("key2")  # Saves $0.003
        
        stats = cache.get_stats()
        expected_savings = 0.001 + 0.002 + 0.003
        assert abs(stats['total_cost_saved'] - expected_savings) < 0.0001
        
        # Hit key1 again
        cache.get("key1")
        stats = cache.get_stats()
        expected_savings += 0.002
        assert abs(stats['total_cost_saved'] - expected_savings) < 0.0001
    
    def test_cache_max_size_eviction(self):
        """Test that cache properly evicts oldest entries when full."""
        cache = ResponseCache(ttl=60, max_size=3)
        
        # Add 3 entries (fill cache)
        for i in range(3):
            response = ChatResponse(
                id=f"test-{i}",
                model="gpt-4o",
                content=f"Response {i}",
                finish_reason="stop",
                usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30, cost_usd=0.001),
                provider="openai",
                created_at=datetime.now(),
                raw_response={}
            )
            cache.set(f"key{i}", response)
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        assert cache.get_stats()['size'] == 3
        
        # Add 4th entry (should evict oldest)
        response = ChatResponse(
            id="test-3",
            model="gpt-4o",
            content="Response 3",
            finish_reason="stop",
            usage=Usage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            provider="openai",
            created_at=datetime.now(),
            raw_response={}
        )
        cache.set("key3", response)
        
        assert cache.get_stats()['size'] == 3
        
        # Oldest entry (key0) should be gone
        assert cache.get("key0") is None
        assert cache.get("key1") is not None
        assert cache.get("key2") is not None
        assert cache.get("key3") is not None
