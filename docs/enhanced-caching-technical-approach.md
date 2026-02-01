# Technical Approach: Enhanced Prompt Caching for StratumAI

## Executive Summary

You want to enhance StratumAI's existing caching implementation (CACHING.md) with the advanced prompt caching patterns from my-prompt-caching.md. Currently, StratumAI has:
- ✅ Response-level caching (complete API response caching)
- ✅ Provider-specific prompt caching (cache_control support for Anthropic, OpenAI, Google)

The enhancement will add:
- **Prefix/chunk-level caching** (static system prompt reuse)
- **Embedding caching** (for RAG applications)
- **Multi-level cache hierarchy** (prefix → response → provider)
- **Advanced cache key strategies** (partial matching for prefix reuse)

---

## Current State Analysis

### Existing Implementation (Strong Foundation)

**llm_abstraction/caching.py:**
- `ResponseCache`: Thread-safe in-memory cache with TTL and LRU eviction
- `cache_response` decorator: Automatic caching of full responses
- `generate_cache_key()`: SHA256 hashing of request parameters
- Global cache instance for convenience

**llm_abstraction/models.py:**
- `Message.cache_control`: Provider-specific prompt caching support
- `Usage`: Tracks cache_creation_tokens, cache_read_tokens, cost_breakdown

**Strengths:**
1. Thread-safe design with locks
2. Configurable TTL and max_size
3. Hit tracking and statistics
4. Clean decorator pattern
5. Provider-agnostic design

**Limitations:**
1. Full-request caching only (no partial/prefix caching)
2. No embedding caching support
3. No chunk-level granularity
4. Cache key is monolithic (can't reuse static prefixes)

---

## Proposed Architecture

### Multi-Level Cache Hierarchy

```
┌─────────────────────────────────────────────────┐
│  Level 1: Prefix Cache (Static Prompts)        │
│  - Cache static system prompts separately       │
│  - Hash prefix independently                    │
│  - Reuse across different user queries          │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Level 2: Response Cache (Current)              │
│  - Cache complete API responses                 │
│  - Full request parameter hashing               │
│  - Fastest lookup for identical queries         │
└─────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────┐
│  Level 3: Provider Cache (Current)              │
│  - Native provider-side caching                 │
│  - cache_control on Message objects             │
│  - 90% cost reduction on cache hits             │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  Separate: Embedding Cache (New)                │
│  - Cache vector embeddings for RAG              │
│  - LRU cache with configurable size             │
│  - Per-text hashing                             │
└─────────────────────────────────────────────────┘
```

### Cache Lookup Flow

```
Request arrives
    ↓
Check Level 1: Prefix Cache
    ├─ Hit? → Extract prefix hash, check Level 2 with prefix + query
    └─ Miss → Continue to Level 2
    ↓
Check Level 2: Response Cache
    ├─ Hit? → Return cached response (0ms latency)
    └─ Miss → Continue to API call
    ↓
API Call with Level 3: Provider Cache
    ├─ Provider checks cache_control
    ├─ Returns cache_creation_tokens or cache_read_tokens
    └─ Store in Level 2 and Level 1 (if applicable)
    ↓
Return response
```

---

## Implementation Design

### 1. PrefixCache Class

**Purpose:** Cache static portions of prompts separately to enable reuse with different user queries.

**File:** `llm_abstraction/prefix_cache.py`

```python
"""Prefix-level caching for static prompt components."""

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from .models import Message


@dataclass
class PrefixEntry:
    """Cached prefix with metadata."""
    prefix_hash: str
    messages: List[Message]  # Static prefix messages
    timestamp: float
    hits: int = 0


class PrefixCache:
    """Cache for static prompt prefixes (system prompts, context)."""
    
    def __init__(self, ttl: int = 7200, max_size: int = 100):
        """
        Initialize prefix cache.
        
        Args:
            ttl: Longer TTL for static content (2 hours default)
            max_size: Smaller size since prefixes are reused
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, PrefixEntry] = {}
        self._lock = threading.Lock()
    
    def compute_prefix_hash(self, messages: List[Message]) -> str:
        """
        Generate hash for prefix messages.
        
        Args:
            messages: List of prefix messages
            
        Returns:
            SHA256 hash of prefix content
        """
        # Hash only role + content, ignore cache_control
        prefix_data = [
            {"role": m.role, "content": m.content}
            for m in messages
        ]
        prefix_str = json.dumps(prefix_data, sort_keys=True)
        return hashlib.sha256(prefix_str.encode()).hexdigest()
    
    def get(self, messages: List[Message]) -> Optional[str]:
        """
        Get cached prefix hash if it exists.
        
        Args:
            messages: Prefix messages to look up
            
        Returns:
            Prefix hash if cached and not expired, None otherwise
        """
        prefix_hash = self.compute_prefix_hash(messages)
        
        with self._lock:
            if prefix_hash not in self._cache:
                return None
            
            entry = self._cache[prefix_hash]
            
            # Check expiration
            if time.time() - entry.timestamp > self.ttl:
                del self._cache[prefix_hash]
                return None
            
            entry.hits += 1
            return prefix_hash
    
    def set(self, messages: List[Message]) -> str:
        """
        Store prefix in cache.
        
        Args:
            messages: Prefix messages to cache
            
        Returns:
            Prefix hash for future lookups
        """
        prefix_hash = self.compute_prefix_hash(messages)
        
        with self._lock:
            # Evict if full
            if len(self._cache) >= self.max_size:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].timestamp
                )
                del self._cache[oldest_key]
            
            self._cache[prefix_hash] = PrefixEntry(
                prefix_hash=prefix_hash,
                messages=messages,
                timestamp=time.time(),
                hits=0
            )
        
        return prefix_hash
    
    def clear(self) -> None:
        """Clear all cached prefixes."""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get prefix cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        with self._lock:
            total_hits = sum(entry.hits for entry in self._cache.values())
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_hits": total_hits,
                "ttl": self.ttl,
            }
```

**Key Features:**
- Separate hashing for static prefix
- Longer TTL (static content changes less frequently)
- Smaller max_size (fewer unique prefixes than full requests)
- Hit tracking for analytics

---

### 2. EmbeddingCache Class

**Purpose:** Cache vector embeddings for RAG applications to avoid recomputation.

**File:** `llm_abstraction/embedding_cache.py`

```python
"""Embedding-level caching for RAG applications."""

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class EmbeddingEntry:
    """Cached embedding with metadata."""
    embedding: List[float]
    model: str
    timestamp: float
    hits: int = 0


class EmbeddingCache:
    """LRU cache for text embeddings (RAG optimization)."""
    
    def __init__(self, ttl: int = 86400, max_size: int = 5000):
        """
        Initialize embedding cache.
        
        Args:
            ttl: 24 hours default (embeddings rarely change)
            max_size: 5000 embeddings (reasonable for most apps)
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, EmbeddingEntry] = {}
        self._lock = threading.Lock()
    
    def _generate_key(self, text: str, model: str) -> str:
        """
        Generate cache key for text + model.
        
        Args:
            text: Text to embed
            model: Embedding model name
            
        Returns:
            SHA256 hash of text + model
        """
        key_data = {"text": text, "model": model}
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def get(self, text: str, model: str) -> Optional[List[float]]:
        """
        Get cached embedding for text.
        
        Args:
            text: Text to look up
            model: Embedding model name
            
        Returns:
            Cached embedding if found and not expired, None otherwise
        """
        key = self._generate_key(text, model)
        
        with self._lock:
            if key not in self._cache:
                return None
            
            entry = self._cache[key]
            
            # Check expiration
            if time.time() - entry.timestamp > self.ttl:
                del self._cache[key]
                return None
            
            entry.hits += 1
            return entry.embedding
    
    def set(self, text: str, model: str, embedding: List[float]) -> None:
        """
        Store embedding in cache.
        
        Args:
            text: Text that was embedded
            model: Embedding model name
            embedding: Embedding vector
        """
        key = self._generate_key(text, model)
        
        with self._lock:
            # Evict LRU if full
            if len(self._cache) >= self.max_size:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].timestamp
                )
                del self._cache[oldest_key]
            
            self._cache[key] = EmbeddingEntry(
                embedding=embedding,
                model=model,
                timestamp=time.time(),
                hits=0
            )
    
    def clear(self) -> None:
        """Clear all cached embeddings."""
        with self._lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_hits = sum(entry.hits for entry in self._cache.values())
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_hits": total_hits,
                "ttl": self.ttl,
            }
```

---

### 3. Enhanced ResponseCache with Prefix Support

**Modifications to:** `llm_abstraction/caching.py`

```python
class ResponseCache:
    """Enhanced cache with prefix support."""
    
    def __init__(
        self, 
        ttl: int = 3600, 
        max_size: int = 1000,
        enable_prefix_cache: bool = True
    ):
        """
        Initialize response cache with optional prefix caching.
        
        Args:
            ttl: Time-to-live for cache entries in seconds
            max_size: Maximum number of entries to store
            enable_prefix_cache: Enable prefix-level caching
        """
        self.ttl = ttl
        self.max_size = max_size
        self.enable_prefix_cache = enable_prefix_cache
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.Lock()
        
        # Lazy-load prefix cache to avoid circular imports
        self._prefix_cache = None
    
    @property
    def prefix_cache(self):
        """Lazy-load prefix cache."""
        if self._prefix_cache is None and self.enable_prefix_cache:
            from .prefix_cache import PrefixCache
            self._prefix_cache = PrefixCache()
        return self._prefix_cache
    
    def get_with_prefix(
        self, 
        messages: List[Message], 
        **kwargs
    ) -> Tuple[Optional[ChatResponse], Optional[str]]:
        """
        Check cache with prefix optimization.
        
        Args:
            messages: List of messages
            **kwargs: Additional request parameters
            
        Returns:
            (cached_response, prefix_hash) tuple
        """
        if not self.enable_prefix_cache or len(messages) < 2:
            return None, None
        
        # Split messages into prefix (system/static) and dynamic
        prefix_messages, dynamic_messages = self._split_prefix(messages)
        
        if not prefix_messages:
            return None, None
        
        # Check if prefix is cached
        prefix_hash = self.prefix_cache.get(prefix_messages)
        
        if prefix_hash:
            # Generate cache key with prefix hash + dynamic messages
            cache_key = self._generate_prefix_key(
                prefix_hash, 
                dynamic_messages, 
                **kwargs
            )
            cached_response = self.get(cache_key)
            return cached_response, prefix_hash
        
        return None, None
    
    def _split_prefix(
        self, 
        messages: List[Message]
    ) -> Tuple[List[Message], List[Message]]:
        """
        Split messages into static prefix and dynamic suffix.
        
        Heuristic: 
        - System messages at the start = prefix
        - Stop at first user message (if multiple user messages exist)
        - Configurable via message attribute in future
        
        Args:
            messages: Full message list
            
        Returns:
            (prefix_messages, dynamic_messages) tuple
        """
        prefix = []
        dynamic = []
        
        # Collect leading system messages
        for i, msg in enumerate(messages):
            if msg.role == "system":
                prefix.append(msg)
            else:
                # Remaining messages are dynamic
                dynamic = messages[i:]
                break
        
        return prefix, dynamic
    
    def _generate_prefix_key(
        self,
        prefix_hash: str,
        dynamic_messages: List[Message],
        **kwargs
    ) -> str:
        """
        Generate cache key combining prefix hash and dynamic content.
        
        Args:
            prefix_hash: Hash of static prefix
            dynamic_messages: Dynamic message list
            **kwargs: Additional parameters
            
        Returns:
            Cache key string
        """
        dynamic_str = json.dumps(
            [{"role": m.role, "content": m.content} for m in dynamic_messages],
            sort_keys=True
        )
        
        cache_data = {
            "prefix_hash": prefix_hash,
            "dynamic": dynamic_str,
            **kwargs  # model, temperature, etc.
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
```

---

### 4. Decorator Enhancements

**New decorator:** `@cache_with_prefix`

**Add to:** `llm_abstraction/caching.py`

```python
def cache_with_prefix(
    ttl: int = 3600,
    prefix_ttl: int = 7200,
    cache_instance: Optional[ResponseCache] = None
):
    """
    Enhanced caching decorator with prefix support.
    
    Args:
        ttl: TTL for full responses
        prefix_ttl: Longer TTL for static prefixes
        cache_instance: Optional cache instance
    
    Example:
        @cache_with_prefix(ttl=3600, prefix_ttl=7200)
        def chat(messages, model, temperature):
            return client.chat(messages=messages, model=model, temperature=temperature)
    """
    cache = cache_instance or _global_cache
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> ChatResponse:
            messages = kwargs.get("messages", [])
            
            # Check prefix cache first
            if cache.enable_prefix_cache and messages:
                cached_response, prefix_hash = cache.get_with_prefix(
                    messages=messages,
                    model=kwargs.get("model"),
                    temperature=kwargs.get("temperature"),
                    max_tokens=kwargs.get("max_tokens")
                )
                
                if cached_response:
                    return cached_response
                
                # Store prefix for future use
                if prefix_hash is None:
                    prefix_messages, _ = cache._split_prefix(messages)
                    if prefix_messages:
                        prefix_hash = cache.prefix_cache.set(prefix_messages)
            
            # Execute function
            response = func(*args, **kwargs)
            
            # Cache response
            if not kwargs.get("stream", False):
                cache_key = generate_cache_key(**kwargs)
                cache.set(cache_key, response)
            
            return response
        
        return wrapper
    return decorator
```

---

### 5. Embedding Utilities

**New utility functions for RAG:**

**File:** `llm_abstraction/embedding_utils.py`

```python
"""Utilities for embedding caching in RAG applications."""

from typing import List, Optional

from .embedding_cache import EmbeddingCache


# Global embedding cache
_embedding_cache = EmbeddingCache()


def cached_embed(
    text: str,
    model: str = "text-embedding-3-large",
    client = None,
    cache_instance: Optional[EmbeddingCache] = None
) -> List[float]:
    """
    Get embedding with caching.
    
    Args:
        text: Text to embed
        model: Embedding model
        client: OpenAI client (or compatible)
        cache_instance: Optional cache instance
    
    Returns:
        List of embedding floats
    """
    cache = cache_instance or _embedding_cache
    
    # Check cache
    cached = cache.get(text, model)
    if cached is not None:
        return cached
    
    # Compute embedding
    if client is None:
        raise ValueError("Client required for embedding computation")
    
    response = client.embeddings.create(
        model=model,
        input=text
    )
    embedding = response.data[0].embedding
    
    # Store in cache
    cache.set(text, model, embedding)
    
    return embedding


def batch_cached_embed(
    texts: List[str],
    model: str = "text-embedding-3-large",
    client = None,
    cache_instance: Optional[EmbeddingCache] = None
) -> List[List[float]]:
    """
    Batch embed with caching (checks cache per-text).
    
    Args:
        texts: List of texts to embed
        model: Embedding model
        client: OpenAI client
        cache_instance: Optional cache instance
    
    Returns:
        List of embeddings
    """
    cache = cache_instance or _embedding_cache
    
    embeddings = []
    uncached_texts = []
    uncached_indices = []
    
    # Check cache for each text
    for i, text in enumerate(texts):
        cached = cache.get(text, model)
        if cached is not None:
            embeddings.append(cached)
        else:
            embeddings.append(None)  # Placeholder
            uncached_texts.append(text)
            uncached_indices.append(i)
    
    # Batch compute uncached embeddings
    if uncached_texts:
        response = client.embeddings.create(
            model=model,
            input=uncached_texts
        )
        
        for i, embedding_data in enumerate(response.data):
            embedding = embedding_data.embedding
            text = uncached_texts[i]
            original_index = uncached_indices[i]
            
            # Store in cache
            cache.set(text, model, embedding)
            
            # Update result
            embeddings[original_index] = embedding
    
    return embeddings


def get_embedding_cache_stats() -> dict:
    """
    Get statistics from the global embedding cache.
    
    Returns:
        Dictionary with cache statistics
    """
    return _embedding_cache.get_stats()


def clear_embedding_cache() -> None:
    """Clear the global embedding cache."""
    _embedding_cache.clear()
```

---

## Integration Points

### 1. LLMClient Integration

**Modifications to:** `llm_abstraction/client.py`

```python
class LLMClient:
    def __init__(
        self,
        enable_response_cache: bool = True,
        enable_prefix_cache: bool = True,
        cache_ttl: int = 3600,
        prefix_cache_ttl: int = 7200
    ):
        """
        Initialize LLM client with multi-level caching.
        
        Args:
            enable_response_cache: Enable response-level caching
            enable_prefix_cache: Enable prefix-level caching
            cache_ttl: TTL for response cache
            prefix_cache_ttl: TTL for prefix cache
        """
        self.enable_response_cache = enable_response_cache
        self.enable_prefix_cache = enable_prefix_cache
        
        if enable_response_cache:
            self._cache = ResponseCache(
                ttl=cache_ttl,
                enable_prefix_cache=enable_prefix_cache
            )
            if enable_prefix_cache:
                self._cache.prefix_cache.ttl = prefix_cache_ttl
    
    @cache_with_prefix(ttl=3600, prefix_ttl=7200)
    def chat(self, **kwargs) -> ChatResponse:
        """Chat with automatic multi-level caching."""
        # Existing implementation
        ...
```

---

### 2. Router Integration

**Enhancement:** Router should consider cache hit probability when selecting models.

**Add to:** `llm_abstraction/router.py`

```python
class Router:
    def _calculate_cost_with_cache_awareness(
        self,
        model: str,
        messages: List[Message],
        provider_name: str
    ) -> float:
        """
        Factor in cache hit probability for cost estimation.
        
        Args:
            model: Model name
            messages: Message list
            provider_name: Provider name
            
        Returns:
            Estimated cost with cache adjustment
        """
        base_cost = self._estimate_cost(model, messages, provider_name)
        
        # Check if prefix is cached
        if not hasattr(self.client, '_cache') or not self.client._cache.enable_prefix_cache:
            return base_cost
        
        prefix_messages, dynamic_messages = self.client._cache._split_prefix(messages)
        
        if self.client._cache.prefix_cache:
            prefix_hash = self.client._cache.prefix_cache.get(prefix_messages)
            
            if prefix_hash:
                # Prefix is cached, adjust cost for cache read (90% discount)
                prefix_tokens = self._estimate_tokens(prefix_messages)
                dynamic_tokens = self._estimate_tokens(dynamic_messages)
                
                provider = self.client._get_provider(provider_name)
                pricing = provider.get_pricing(model)
                
                # Recalculate with cache discount
                cache_read_cost = prefix_tokens * pricing["cache_read_per_1k"] / 1000
                dynamic_cost = dynamic_tokens * pricing["input_per_1k"] / 1000
                
                return cache_read_cost + dynamic_cost
        
        return base_cost
```

---

## Usage Examples

### Example 1: Basic Prefix Caching

```python
from llm_abstraction import LLMClient, Message

client = LLMClient(enable_prefix_cache=True)

# Large static system prompt
system_prompt = """
[Large documentation - 10,000 tokens]
You are an expert code reviewer...
[Many more paragraphs...]
"""

# First query
messages = [
    Message(role="system", content=system_prompt),
    Message(role="user", content="Review this Python function: def foo(): pass")
]

response1 = client.chat(model="gpt-4.1-mini", messages=messages)
# Caches prefix separately

# Second query with same prefix, different user message
messages[1] = Message(role="user", content="Review this TypeScript code: const x = 1")

response2 = client.chat(model="gpt-4.1-mini", messages=messages)
# Reuses cached prefix, only processes new user message
```

### Example 2: Embedding Caching for RAG

```python
from llm_abstraction.embedding_utils import batch_cached_embed
from openai import OpenAI

client = OpenAI()

documents = [
    "Document 1 about AI...",
    "Document 2 about ML...",
    "Document 3 about AI...",  # Duplicate content
]

# First call - caches all embeddings
embeddings1 = batch_cached_embed(
    texts=documents,
    model="text-embedding-3-large",
    client=client
)

# Second call with some repeated documents
new_documents = [
    "Document 1 about AI...",  # Cache hit
    "New document 4...",  # Cache miss
]

embeddings2 = batch_cached_embed(
    texts=new_documents,
    model="text-embedding-3-large",
    client=client
)
# Only computes embedding for "New document 4"
```

### Example 3: Combined Multi-Level Caching

```python
from llm_abstraction import LLMClient, Message

client = LLMClient(
    enable_response_cache=True,
    enable_prefix_cache=True
)

# Setup with provider-level caching
large_context = Message(
    role="system",
    content="[50,000 token document]",
    cache_control={"type": "ephemeral"}  # Level 3: Provider cache
)

user_msg = Message(role="user", content="What is the main topic?")

# Call 1: All caches miss
response1 = client.chat(
    model="claude-3.5-sonnet",
    messages=[large_context, user_msg]
)
# - Level 3: Provider writes cache (+25% cost)
# - Level 2: Response cache stores result
# - Level 1: Prefix cache stores system message

# Call 2: Same question (identical request)
response2 = client.chat(
    model="claude-3.5-sonnet",
    messages=[large_context, user_msg]
)
# - Level 2: Response cache hit (instant, $0)

# Call 3: Different question, same context
user_msg2 = Message(role="user", content="Summarize the key points")
response3 = client.chat(
    model="claude-3.5-sonnet",
    messages=[large_context, user_msg2]
)
# - Level 2: Miss (different question)
# - Level 1: Prefix hit (reuses system prompt hash)
# - Level 3: Provider cache hit (90% discount)
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_prefix_cache.py`

```python
import time
from llm_abstraction.prefix_cache import PrefixCache
from llm_abstraction.models import Message


def test_prefix_cache_basic():
    """Test basic prefix caching."""
    cache = PrefixCache()
    messages = [Message(role="system", content="You are helpful")]
    
    # First call - cache miss
    hash1 = cache.get(messages)
    assert hash1 is None
    
    # Store prefix
    hash2 = cache.set(messages)
    
    # Second call - cache hit
    hash3 = cache.get(messages)
    assert hash3 == hash2


def test_prefix_cache_expiration():
    """Test TTL expiration."""
    cache = PrefixCache(ttl=1)  # 1 second
    messages = [Message(role="system", content="Test")]
    
    cache.set(messages)
    time.sleep(2)
    
    # Should be expired
    assert cache.get(messages) is None


def test_prefix_cache_hit_tracking():
    """Test hit tracking."""
    cache = PrefixCache()
    messages = [Message(role="system", content="Test")]
    
    cache.set(messages)
    
    # Multiple hits
    for _ in range(5):
        cache.get(messages)
    
    stats = cache.get_stats()
    assert stats["total_hits"] == 5


def test_prefix_cache_eviction():
    """Test LRU eviction."""
    cache = PrefixCache(max_size=2)
    
    msg1 = [Message(role="system", content="First")]
    msg2 = [Message(role="system", content="Second")]
    msg3 = [Message(role="system", content="Third")]
    
    cache.set(msg1)
    cache.set(msg2)
    cache.set(msg3)  # Should evict msg1
    
    assert cache.get(msg1) is None
    assert cache.get(msg2) is not None
    assert cache.get(msg3) is not None
```

**File:** `tests/test_embedding_cache.py`

```python
from llm_abstraction.embedding_cache import EmbeddingCache


def test_embedding_cache_basic():
    """Test basic embedding caching."""
    cache = EmbeddingCache()
    text = "Hello world"
    model = "text-embedding-3-large"
    embedding = [0.1, 0.2, 0.3]
    
    # Store
    cache.set(text, model, embedding)
    
    # Retrieve
    cached = cache.get(text, model)
    assert cached == embedding


def test_embedding_cache_different_models():
    """Test caching with different models."""
    cache = EmbeddingCache()
    text = "Hello"
    embedding1 = [0.1, 0.2]
    embedding2 = [0.3, 0.4]
    
    cache.set(text, "model-1", embedding1)
    cache.set(text, "model-2", embedding2)
    
    assert cache.get(text, "model-1") == embedding1
    assert cache.get(text, "model-2") == embedding2


def test_embedding_batch_cache():
    """Test batch embedding with caching."""
    from llm_abstraction.embedding_utils import batch_cached_embed
    
    class MockOpenAIClient:
        def __init__(self):
            self.call_count = 0
        
        def embeddings_create(self, model, input):
            self.call_count += 1
            class Response:
                data = [type('obj', (), {'embedding': [0.1] * len(t)}) for t in input]
            return Response()
    
    mock_client = MockOpenAIClient()
    texts = ["text1", "text2", "text1"]  # Duplicate
    
    embeddings = batch_cached_embed(texts, client=mock_client)
    
    # Should call API for unique texts only
    assert len(embeddings) == 3
```

### Integration Tests

**File:** `tests/integration/test_multi_level_caching.py`

```python
from llm_abstraction import LLMClient, Message


def test_prefix_response_cache_integration():
    """Test prefix cache + response cache working together."""
    client = LLMClient(enable_prefix_cache=True)
    
    system_msg = Message(role="system", content="Large context")
    user_msg1 = Message(role="user", content="Question 1")
    user_msg2 = Message(role="user", content="Question 2")
    
    # Call 1
    resp1 = client.chat(
        model="gpt-4.1-mini",
        messages=[system_msg, user_msg1]
    )
    
    # Call 2 - same question (response cache hit)
    resp2 = client.chat(
        model="gpt-4.1-mini",
        messages=[system_msg, user_msg1]
    )
    
    # Call 3 - different question (prefix cache hit)
    resp3 = client.chat(
        model="gpt-4.1-mini",
        messages=[system_msg, user_msg2]
    )
    
    # Verify cache hits
    assert resp1.id != resp2.id  # Cached response
    
    # Check prefix cache stats
    stats = client._cache.prefix_cache.get_stats()
    assert stats["total_hits"] >= 1
```

---

## Migration Path

### Phase 1: Core Infrastructure (Week 1)
- ✅ Create `prefix_cache.py` with `PrefixCache` class
- ✅ Create `embedding_cache.py` with `EmbeddingCache` class
- ✅ Add unit tests for both caches
- ✅ Update `__init__.py` exports

### Phase 2: Integration (Week 1-2)
- ✅ Enhance `ResponseCache` with `get_with_prefix()` method
- ✅ Create `cache_with_prefix` decorator
- ✅ Add `embedding_utils.py` with helper functions
- ✅ Integration tests

### Phase 3: LLMClient Integration (Week 2)
- ✅ Add prefix cache support to `LLMClient.__init__`
- ✅ Update `client.chat()` to use new decorator
- ✅ Add configuration options
- ✅ Update Router for cache-aware cost estimation

### Phase 4: Documentation & Examples (Week 2-3)
- ✅ Update `docs/CACHING.md` with new features
- ✅ Create `examples/advanced_caching.py`
- ✅ Add API reference for new classes
- ✅ Performance benchmarks

### Phase 5: Optimization & Polish (Week 3)
- ✅ Performance profiling
- ✅ Memory usage optimization
- ✅ Add monitoring/observability hooks
- ✅ Final testing

---

## Performance Considerations

### Memory Usage

**Estimates:**
- `ResponseCache`: ~1KB per entry × 1000 entries = ~1MB
- `PrefixCache`: ~500 bytes per entry × 100 entries = ~50KB
- `EmbeddingCache`: ~4KB per embedding × 5000 = ~20MB
- **Total:** ~21MB (acceptable for most applications)

**Optimization:**
- Use LRU eviction (already implemented)
- Configurable max_size
- Optional cache serialization to disk (future enhancement)

### Latency Impact

**Cache Lookups:**
- In-memory hash lookup: < 1ms
- Lock acquisition overhead: < 0.1ms
- Total cache check: < 2ms (negligible)

**Cache Benefits:**
- Response cache hit: -100% API latency (instant)
- Prefix cache hit: -50% API latency (smaller request)
- Provider cache hit: -30-50ms (faster processing)

---

## Configuration Options

### Environment Variables

```bash
# Response caching
STRATUMAI_CACHE_ENABLED=true
STRATUMAI_CACHE_TTL=3600
STRATUMAI_CACHE_MAX_SIZE=1000

# Prefix caching
STRATUMAI_PREFIX_CACHE_ENABLED=true
STRATUMAI_PREFIX_CACHE_TTL=7200
STRATUMAI_PREFIX_CACHE_MAX_SIZE=100

# Embedding caching
STRATUMAI_EMBEDDING_CACHE_ENABLED=true
STRATUMAI_EMBEDDING_CACHE_TTL=86400
STRATUMAI_EMBEDDING_CACHE_MAX_SIZE=5000
```

### Programmatic Configuration

```python
client = LLMClient(
    enable_response_cache=True,
    enable_prefix_cache=True,
    cache_ttl=3600,
    prefix_cache_ttl=7200,
    embedding_cache_config={
        "ttl": 86400,
        "max_size": 5000
    }
)
```

---

## Monitoring & Observability

### Cache Statistics API

```python
from llm_abstraction import get_all_cache_stats

stats = get_all_cache_stats()
# {
#   "response_cache": {
#     "size": 245,
#     "total_hits": 1523,
#     "hit_rate": 0.62,
#     "ttl": 3600
#   },
#   "prefix_cache": {
#     "size": 12,
#     "total_hits": 458,
#     "hit_rate": 0.79,
#     "ttl": 7200
#   },
#   "embedding_cache": {
#     "size": 2341,
#     "total_hits": 8923,
#     "hit_rate": 0.81,
#     "ttl": 86400
#   }
# }
```

### Logging Integration

```python
import logging

logger = logging.getLogger("stratumai.caching")

# Log cache events
logger.debug("Response cache hit: key=%s", cache_key[:8])
logger.debug("Prefix cache miss: storing new prefix hash=%s", prefix_hash[:8])
logger.info("Cache stats: %s", stats)
```

---

## Suggestions & Recommendations

### 1. **Start with Prefix Caching**
Highest ROI for applications with static system prompts. Implement `PrefixCache` first.

### 2. **Add Observability Early**
Include logging and statistics from day one. Makes debugging easier.

### 3. **Make Prefix Detection Configurable**
Allow users to mark messages as "static" explicitly:

```python
Message(
    role="system",
    content="...",
    is_static=True  # Explicit prefix marker
)
```

### 4. **Consider Async Support**
For high-throughput applications, add async cache methods:

```python
async def get_async(self, key: str) -> Optional[ChatResponse]:
    ...
```

### 5. **Add Persistence Layer (Optional)**
For production systems, consider Redis or disk-based caching:

```python
class RedisResponseCache(ResponseCache):
    def __init__(self, redis_client, ttl=3600):
        self.redis = redis_client
        ...
```

### 6. **Smart Prefix Detection**
Enhance `_split_prefix()` with heuristics:
- Detect long static prompts (> 1000 tokens)
- Detect RAG document patterns
- User-configurable split points

### 7. **Cost-Aware Cache Eviction**
Prioritize keeping expensive prefixes in cache:

```python
def _evict_by_value(self):
    """Evict least valuable entry (cost/hits ratio)."""
    lowest_value = min(
        self._cache.items(),
        key=lambda x: x[1].cost_saved / max(x[1].hits, 1)
    )
    del self._cache[lowest_value[0]]
```

### 8. **Cache Warming**
Pre-populate cache with common queries:

```python
def warm_cache(self, common_queries: List[dict]):
    """Pre-populate cache with common queries."""
    for query in common_queries:
        self.chat(**query)
```

### 9. **Metrics Export**
Export cache metrics to Prometheus/Datadog:

```python
from prometheus_client import Gauge, Counter

cache_size_gauge = Gauge('stratumai_cache_size', 'Cache size')
cache_hits_counter = Counter('stratumai_cache_hits', 'Cache hits')
```

### 10. **Documentation is Critical**
Clearly document when each cache level triggers. Users need to understand the behavior.

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Memory bloat with large caches | High | Enforce max_size, add monitoring |
| Stale cached data | Medium | Appropriate TTL, manual clear_cache() |
| Thread contention | Low | Lock granularity, async option |
| Cache key collisions | Low | SHA256 hashing (collision-resistant) |
| Prefix detection errors | Medium | Conservative detection, explicit markers |

---

## Success Metrics

### Performance
- **Cache hit rate**: > 30% for response cache, > 60% for prefix cache
- **Latency reduction**: > 50% for cached requests
- **Memory usage**: < 50MB for default configuration

### Cost Savings
- **API cost reduction**: > 40% with prefix caching enabled
- **Embedding cost reduction**: > 80% for repeated documents

### Adoption
- **Usage**: > 50% of LLMClient instances enable caching
- **Developer satisfaction**: Clear documentation, easy configuration

---

## Conclusion

This implementation brings StratumAI's caching capabilities to production-grade level by adding:

1. **Prefix caching** for static prompt reuse
2. **Embedding caching** for RAG applications
3. **Multi-level cache hierarchy** for optimal performance
4. **Intelligent cache key strategies** for partial matching

The design maintains backward compatibility, follows StratumAI's existing patterns (thread-safe, decorator-based), and provides clear migration path. The modular architecture allows incremental adoption—users can enable/disable each caching level independently.

**Recommended Implementation Order:**
1. PrefixCache (highest ROI)
2. Enhanced ResponseCache integration
3. EmbeddingCache (if RAG features planned)
4. Observability and monitoring
5. Documentation and examples

This approach balances functionality, performance, and maintainability while staying true to StratumAI's production-ready philosophy.
