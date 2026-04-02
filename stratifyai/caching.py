"""Caching utilities for LLM responses."""

import hashlib
import json
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

from .models import ChatResponse, Usage


@dataclass
class CacheEntry:
    """Entry in the response cache."""

    response: ChatResponse
    timestamp: float
    hits: int = 0
    cost_saved: float = 0.0  # Total cost saved from this entry


class ResponseCache:
    """Thread-safe in-memory cache for LLM responses."""

    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        """
        Initialize response cache.

        Args:
            ttl: Time-to-live for cache entries in seconds
            max_size: Maximum number of entries to store
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        self._total_misses: int = 0
        self._total_cost_saved: float = 0.0

    def get(self, key: str) -> ChatResponse | None:
        """
        Get response from cache.

        Args:
            key: Cache key

        Returns:
            Cached response if found and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                self._total_misses += 1
                return None

            entry = self._cache[key]

            # Check if expired
            if time.time() - entry.timestamp > self.ttl:
                del self._cache[key]
                self._total_misses += 1
                return None

            # Update hit count and cost saved
            entry.hits += 1
            if hasattr(entry.response, "usage") and hasattr(
                entry.response.usage, "cost_usd"
            ):
                cost = entry.response.usage.cost_usd
                entry.cost_saved += cost
                self._total_cost_saved += cost

            return entry.response

    def set(self, key: str, response: ChatResponse) -> None:
        """
        Store response in cache.

        Args:
            key: Cache key
            response: Response to cache
        """
        with self._lock:
            # Evict oldest entry if cache is full
            if len(self._cache) >= self.max_size:
                oldest_key = min(
                    self._cache.keys(), key=lambda k: self._cache[k].timestamp
                )
                del self._cache[oldest_key]

            self._cache[key] = CacheEntry(
                response=response, timestamp=time.time(), hits=0
            )

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._total_misses = 0
            self._total_cost_saved = 0.0

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats including hits, misses, and cost savings
        """
        with self._lock:
            total_hits = sum(entry.hits for entry in self._cache.values())
            total_requests = total_hits + self._total_misses
            hit_rate = (
                (total_hits / total_requests * 100) if total_requests > 0 else 0.0
            )

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_hits": total_hits,
                "total_misses": self._total_misses,
                "total_requests": total_requests,
                "hit_rate": hit_rate,
                "total_cost_saved": self._total_cost_saved,
                "ttl": self.ttl,
            }

    def get_entries(self) -> list[dict[str, Any]]:
        """
        Get detailed information about cache entries.

        Returns:
            List of cache entry details
        """
        with self._lock:
            entries = []
            for key, entry in self._cache.items():
                age = time.time() - entry.timestamp
                entries.append(
                    {
                        "key": key[:16] + "...",  # Truncate hash for display
                        "model": entry.response.model
                        if hasattr(entry.response, "model")
                        else "unknown",
                        "provider": entry.response.provider
                        if hasattr(entry.response, "provider")
                        else "unknown",
                        "hits": entry.hits,
                        "cost_saved": entry.cost_saved,
                        "age_seconds": int(age),
                        "expires_in": int(self.ttl - age),
                    }
                )

            # Sort by hits (most popular first)
            entries.sort(key=lambda x: x["hits"], reverse=True)
            return entries


class PersistentResponseCache:
    """SQLite-backed persistent cache for LLM responses.

    Survives server restarts.  Provides the same interface as
    :class:`ResponseCache` so it can be used as a drop-in replacement.

    Args:
        db_path: Path to the SQLite database file.
            Defaults to ``~/.stratifyai/cache.db``.
        ttl: Time-to-live for cache entries in seconds.
        max_size: Maximum number of entries to store.
    """

    def __init__(
        self,
        db_path: str = "~/.stratifyai/cache.db",
        ttl: int = 3600,
        max_size: int = 1000,
    ) -> None:
        self.ttl = ttl
        self.max_size = max_size
        resolved = Path(db_path).expanduser()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(resolved)
        self._lock = threading.Lock()
        self._init_db()

    # ---- DB helpers -------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key          TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL,
                    timestamp    REAL NOT NULL,
                    hits         INTEGER NOT NULL DEFAULT 0,
                    cost_saved   REAL NOT NULL DEFAULT 0.0
                )
                """
            )
            conn.commit()

    # ---- Serialisation ----------------------------------------------------

    @staticmethod
    def _serialize_response(response: ChatResponse) -> str:
        """Serialize a ``ChatResponse`` to a JSON string."""
        data = {
            "id": response.id,
            "model": response.model,
            "content": response.content,
            "finish_reason": response.finish_reason,
            "provider": response.provider,
            "created_at": response.created_at.isoformat(),
            "raw_response": response.raw_response,
            "latency_ms": response.latency_ms,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "cached_tokens": response.usage.cached_tokens,
                "cache_creation_tokens": response.usage.cache_creation_tokens,
                "cache_read_tokens": response.usage.cache_read_tokens,
                "reasoning_tokens": response.usage.reasoning_tokens,
                "cost_usd": response.usage.cost_usd,
            },
        }
        return json.dumps(data, default=str)

    @staticmethod
    def _deserialize_response(data_str: str) -> ChatResponse:
        """Reconstruct a ``ChatResponse`` from its JSON string."""
        d = json.loads(data_str)
        usage = Usage(
            prompt_tokens=d["usage"]["prompt_tokens"],
            completion_tokens=d["usage"]["completion_tokens"],
            total_tokens=d["usage"]["total_tokens"],
            cached_tokens=d["usage"].get("cached_tokens", 0),
            cache_creation_tokens=d["usage"].get("cache_creation_tokens", 0),
            cache_read_tokens=d["usage"].get("cache_read_tokens", 0),
            reasoning_tokens=d["usage"].get("reasoning_tokens", 0),
            cost_usd=d["usage"].get("cost_usd", 0.0),
        )
        return ChatResponse(
            id=d["id"],
            model=d["model"],
            content=d["content"],
            finish_reason=d["finish_reason"],
            usage=usage,
            provider=d["provider"],
            created_at=datetime.fromisoformat(d["created_at"]),
            raw_response=d.get("raw_response", {}),
            latency_ms=d.get("latency_ms"),
        )

    # ---- Public interface (matches ResponseCache) -------------------------

    def get(self, key: str) -> ChatResponse | None:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT response_json, timestamp, hits, cost_saved FROM cache WHERE key = ?",
                    (key,),
                ).fetchone()
                if row is None:
                    return None

                response_json, ts, hits, cost_saved = row

                # Expire stale entries
                if time.time() - ts > self.ttl:
                    conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                    conn.commit()
                    return None

                response = self._deserialize_response(response_json)
                cost = (
                    response.usage.cost_usd
                    if hasattr(response.usage, "cost_usd")
                    else 0.0
                )
                conn.execute(
                    "UPDATE cache SET hits = hits + 1, cost_saved = cost_saved + ? WHERE key = ?",
                    (cost, key),
                )
                conn.commit()
                return response

    def set(self, key: str, response: ChatResponse) -> None:
        with self._lock:
            with self._connect() as conn:
                # Evict oldest if at capacity
                count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
                if count >= self.max_size:
                    conn.execute(
                        "DELETE FROM cache WHERE key = "
                        "(SELECT key FROM cache ORDER BY timestamp ASC LIMIT 1)"
                    )

                response_json = self._serialize_response(response)
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, response_json, timestamp, hits, cost_saved) "
                    "VALUES (?, ?, ?, 0, 0.0)",
                    (key, response_json, time.time()),
                )
                conn.commit()

    def clear(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM cache")
                conn.commit()

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT COUNT(*), COALESCE(SUM(hits), 0), COALESCE(SUM(cost_saved), 0.0) FROM cache"
                ).fetchone()
                size, total_hits, total_cost_saved = row
                # Misses are not tracked in persistent cache (would need a separate counter table)
                return {
                    "size": size,
                    "max_size": self.max_size,
                    "total_hits": total_hits,
                    "total_cost_saved": total_cost_saved,
                    "ttl": self.ttl,
                    "backend": "sqlite",
                    "db_path": self._db_path,
                }

    def get_entries(self) -> list[dict[str, Any]]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT key, response_json, timestamp, hits, cost_saved "
                    "FROM cache ORDER BY hits DESC LIMIT 100"
                ).fetchall()
                entries = []
                now = time.time()
                for key, rj, ts, hits, cs in rows:
                    resp = self._deserialize_response(rj)
                    age = now - ts
                    entries.append(
                        {
                            "key": key[:16] + "...",
                            "model": resp.model,
                            "provider": resp.provider,
                            "hits": hits,
                            "cost_saved": cs,
                            "age_seconds": int(age),
                            "expires_in": int(self.ttl - age),
                        }
                    )
                return entries


# Global cache instance
_global_cache = ResponseCache()


def generate_cache_key(
    model: str,
    messages: list,
    temperature: float,
    max_tokens: int | None = None,
    **kwargs,
) -> str:
    """
    Generate a unique cache key from request parameters.

    Args:
        model: Model name
        messages: List of messages
        temperature: Temperature parameter
        max_tokens: Maximum tokens
        **kwargs: Additional parameters

    Returns:
        SHA256 hash of the request parameters
    """
    # Convert messages to hashable format
    messages_str = json.dumps(
        [
            {"role": m.role, "content": m.content} if hasattr(m, "role") else m
            for m in messages
        ],
        sort_keys=True,
    )

    # Include relevant parameters
    cache_data = {
        "model": model,
        "messages": messages_str,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    # Add any additional kwargs that affect the response
    for key in sorted(kwargs.keys()):
        if key not in ["stream", "extra_params"]:  # Skip non-deterministic params
            cache_data[key] = kwargs[key]

    # Generate hash
    cache_str = json.dumps(cache_data, sort_keys=True)
    return hashlib.sha256(cache_str.encode()).hexdigest()


def cache_response(
    ttl: int = 3600,
    cache_instance: ResponseCache | None = None,
    cache_backend: PersistentResponseCache | None = None,
):
    """
    Decorator to cache async LLM responses.

    Args:
        ttl: Time-to-live for cache entries in seconds. When using ``cache_instance``,
            the TTL should match the cache's configured TTL, as the cache's TTL is
            used for expiration checking.
        cache_instance: Optional in-memory cache instance (uses global if None)
        cache_backend: Optional persistent cache backend (takes precedence over
            ``cache_instance`` if provided)

    Returns:
        Decorated async function

    Example:
        @cache_response(ttl=3600)
        async def chat(self, request: ChatRequest) -> ChatResponse:
            return await self.provider.chat_completion(request)

    Note:
        When using a custom ``cache_instance``, expiration is controlled by the
        cache's TTL, not the decorator's ``ttl`` parameter. Ensure both are set
        to the same value for consistent behavior.
    """
    # Persistent backend takes precedence if provided
    backend = cache_backend
    cache = cache_instance or _global_cache

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> ChatResponse:
            # Extract request parameters
            # Handle both ChatRequest object and individual parameters
            if args and hasattr(args[0], "model"):
                request = args[0]
                cache_key = generate_cache_key(
                    model=request.model,
                    messages=request.messages,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
            else:
                cache_key = generate_cache_key(**kwargs)

            # --- Persistent backend path (PersistentResponseCache) ---
            if backend is not None:
                cached = backend.get(cache_key)
                if cached is not None:
                    return cached

                response = await func(*args, **kwargs)
                if not kwargs.get("stream", False):
                    backend.set(cache_key, response)
                return response

            # --- In-memory path (ResponseCache) ---
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute async function
            response = await func(*args, **kwargs)

            # Cache response (only if not streaming)
            if not kwargs.get("stream", False):
                cache.set(cache_key, response)

            return response

        return async_wrapper

    return decorator


def get_cache_stats() -> dict[str, Any]:
    """
    Get statistics from the global cache.

    Returns:
        Dictionary with cache statistics
    """
    return _global_cache.get_stats()


def get_cache_entries() -> list[dict[str, Any]]:
    """
    Get detailed information about cache entries.

    Returns:
        List of cache entry details
    """
    return _global_cache.get_entries()


def clear_cache() -> None:
    """Clear the global cache."""
    _global_cache.clear()
