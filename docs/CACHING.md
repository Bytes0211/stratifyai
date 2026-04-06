# Prompt Caching in StratifyAI

This document explains the prompt caching features in StratifyAI, including both response caching and provider-specific prompt caching (Anthropic, OpenAI, Google).

## Table of Contents

1. [Overview](#overview)
2. [Response Caching](#response-caching)
3. [Provider Prompt Caching](#provider-prompt-caching)
4. [Cost Savings](#cost-savings)
5. [API Reference](#api-reference)
6. [Examples](#examples)

---

## Overview

StratifyAI provides two levels of caching:

1. **Response Caching**: In-memory cache of complete API responses for repeated identical requests
2. **Provider Prompt Caching**: Native support for provider-specific prompt caching (Anthropic, OpenAI, Google)

Both caching mechanisms help reduce costs and improve response times.

---

## Response Caching

Response caching stores complete API responses in memory and returns cached results for identical requests.

### Features

- **Thread-safe in-memory cache**: Safe for concurrent requests
- **Configurable TTL**: Set time-to-live for cache entries (default: 3600 seconds)
- **Size limits**: Automatic eviction of oldest entries when max size is reached
- **Hit tracking**: Monitor cache effectiveness with built-in statistics
- **Decorator support**: Easy integration with `@cache_response` decorator

### Basic Usage

```python
from stratifyai import LLMClient, Message

client = LLMClient()

# First call - makes actual API request
response1 = client.chat(
    model="gpt-4.1-mini",
    messages=[Message(role="user", content="What is 2+2?")],
    temperature=0.7,
)

# Second call with identical parameters - uses cache
response2 = client.chat(
    model="gpt-4.1-mini",
    messages=[Message(role="user", content="What is 2+2?")],
    temperature=0.7,
)
# response2 is retrieved from cache (no API call)
```

### Custom Cache Configuration

```python
from stratifyai import ResponseCache, cache_response, LLMClient

# Create custom cache with 5-minute TTL and max 100 entries
custom_cache = ResponseCache(ttl=300, max_size=100)

client = LLMClient()

@cache_response(ttl=300, cache_instance=custom_cache)
def cached_chat(**kwargs):
    return client.chat(**kwargs)

# Use the cached function
response = cached_chat(
    model="gpt-4.1-mini",
    messages=[Message(role="user", content="Hello")],
)
```

### Cache Management

```python
from stratifyai import get_cache_stats, clear_cache

# Get cache statistics
stats = get_cache_stats()
print(f"Cache size: {stats['size']}")
print(f"Total hits: {stats['total_hits']}")
print(f"TTL: {stats['ttl']} seconds")

# Clear cache
clear_cache()
```

---

## Provider Prompt Caching

Provider-specific prompt caching allows you to cache large context blocks at the provider level, significantly reducing costs for repeated use of the same context.

### Supported Providers

| Provider | Support | Cache Write Cost | Cache Read Cost | Notes |
|----------|---------|------------------|-----------------|-------|
| OpenAI | ✅ Yes | +25% of input | -90% of input | gpt-4.1+, gpt-5 series |
| Anthropic | ✅ Yes | +25% of input | -90% of input | Claude 3+ models |
| Google | ✅ Yes | +25% of input | -90% of input | Gemini 2.5+ models |
| DeepSeek | ❌ No | N/A | N/A | Not supported |
| Groq | ❌ No | N/A | N/A | Not supported |
| Grok | ❌ No | N/A | N/A | Not supported |
| OpenRouter | Varies | Varies | Varies | Depends on underlying model |
| Ollama | ❌ No | N/A | N/A | Local models |

### How It Works

1. **First request**: Provider caches marked content and charges cache write cost (+25%)
2. **Subsequent requests**: Provider reads from cache and charges cache read cost (-90%)
3. **Cost savings**: Significant savings on repeated use of large contexts (documents, codebases, etc.)

### Usage with Cache Control

```python
from stratifyai import LLMClient, Message

client = LLMClient()

# Large context you want to cache
long_document = """
[Your 50,000+ token document here]
This is a comprehensive guide...
[Many more paragraphs...]
"""

# Mark the long context for caching
messages = [
    Message(
        role="system",
        content=long_document,
        cache_control={"type": "ephemeral"}  # Enable caching
    ),
    Message(
        role="user",
        content="Summarize the key points from the guide above."
    ),
]

# First call - writes to provider cache
response1 = client.chat(
    model="gpt-4.1-mini",
    messages=messages,
    temperature=0.7,
)

print(f"Cache creation tokens: {response1.usage.cache_creation_tokens}")
print(f"Cost breakdown: {response1.usage.cost_breakdown}")

# Second call with same cached context, different question
messages[1] = Message(
    role="user",
    content="What are the main challenges discussed?"
)

response2 = client.chat(
    model="gpt-4.1-mini",
    messages=messages,
    temperature=0.7,
)

print(f"Cache read tokens: {response2.usage.cache_read_tokens}")
print(f"Cost savings: ${response1.usage.cost_usd - response2.usage.cost_usd:.4f}")
```

### Checking Cache Support

```python
from stratifyai.providers.openai import OpenAIProvider

provider = OpenAIProvider(api_key="your-key")

# Check if model supports caching
if provider.supports_caching("gpt-4.1-mini"):
    print("This model supports prompt caching!")
```

---

## Cost Savings

### Response Caching Savings

Response caching provides 100% cost savings for cached requests (no API call is made).

**Example Scenario:**
- 5 API calls with 2 repeated queries
- Without caching: 5 API calls = $0.0015
- With caching: 3 API calls = $0.0009
- **Savings: $0.0006 (40%)**

### Provider Prompt Caching Savings

Provider prompt caching provides significant savings for large context reuse.

**Example: GPT-4.1-mini with 50,000-token document**

| Scenario | Input Tokens | Cache Write Tokens | Cache Read Tokens | Cost |
|----------|-------------|-------------------|------------------|------|
| First call (no cache) | 50,000 | 0 | 0 | $0.0075 |
| First call (cache write) | 0 | 50,000 | 0 | $0.0094 |
| Subsequent calls (cache read) | 0 | 0 | 50,000 | $0.0008 |

**Cost per call:**
1. First call with caching: $0.0094 (cache write premium)
2. Subsequent calls: $0.0008 (90% discount)
3. Break-even point: 2 calls
4. After 10 calls with same context:
   - Without caching: $0.075
   - With caching: $0.0094 + (9 × $0.0008) = $0.0166
   - **Savings: $0.0584 (78%)**

### Combined Caching Strategy

For maximum savings, combine both caching methods:

1. **Response caching**: Eliminates API calls for identical queries
2. **Provider caching**: Reduces costs for repeated context with different queries

```python
from stratifyai import LLMClient, Message, cache_response, ResponseCache

# Enable response caching
custom_cache = ResponseCache(ttl=600)  # 10-minute TTL

@cache_response(cache_instance=custom_cache)
def cached_chat(**kwargs):
    return client.chat(**kwargs)

# Use provider prompt caching for large contexts
large_context = Message(
    role="system",
    content="[Large document]",
    cache_control={"type": "ephemeral"}
)

# This combines both caching strategies
response = cached_chat(
    model="gpt-4.1-mini",
    messages=[large_context, Message(role="user", content="Question")],
)
```

---

## API Reference

### ResponseCache

Thread-safe in-memory cache for LLM responses.

```python
class ResponseCache:
    def __init__(self, ttl: int = 3600, max_size: int = 1000):
        """
        Initialize response cache.
        
        Args:
            ttl: Time-to-live in seconds (default: 3600)
            max_size: Maximum cache entries (default: 1000)
        """
    
    def get(self, key: str) -> Optional[ChatResponse]:
        """Get cached response by key."""
    
    def set(self, key: str, response: ChatResponse) -> None:
        """Store response in cache."""
    
    def clear(self) -> None:
        """Clear all cache entries."""
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
```

### cache_response Decorator

Decorator to cache LLM responses.

```python
def cache_response(
    ttl: int = 3600,
    cache_instance: Optional[ResponseCache] = None
):
    """
    Decorator to cache LLM responses.
    
    Args:
        ttl: Time-to-live in seconds
        cache_instance: Optional cache instance (uses global if None)
    
    Usage:
        @cache_response(ttl=600)
        def my_chat_function(**kwargs):
            return client.chat(**kwargs)
    """
```

### Utility Functions

```python
def get_cache_stats() -> Dict[str, Any]:
    """Get statistics from the global cache."""

def clear_cache() -> None:
    """Clear the global cache."""

def generate_cache_key(
    model: str,
    messages: list,
    temperature: float,
    max_tokens: Optional[int] = None,
    **kwargs
) -> str:
    """Generate cache key from request parameters."""
```

### Message with Cache Control

```python
from stratifyai import Message

message = Message(
    role="system",
    content="Large context to cache",
    cache_control={"type": "ephemeral"}  # Enable provider caching
)
```

### Usage Model Extensions

The `Usage` model includes cache-related fields:

```python
@dataclass
class Usage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int = 0              # Total cached tokens
    cache_creation_tokens: int = 0      # Tokens written to cache
    cache_read_tokens: int = 0          # Tokens read from cache
    reasoning_tokens: int = 0
    cost_usd: float = 0.0
    cost_breakdown: Optional[dict] = None  # Detailed cost breakdown
```

---

## Examples

See `examples/caching_examples.py` for comprehensive examples including:

1. **Basic Response Caching**: Simple caching of API responses
2. **Custom Cache with TTL**: Custom cache configuration
3. **Prompt Caching with Cache Control**: Provider-specific caching
4. **Cache Management**: Monitoring and managing cache
5. **Cost Comparison**: Measuring cost savings

Run the examples:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run examples (requires API keys)
python examples/caching_examples.py
```

---

## Best Practices

### When to Use Response Caching

✅ **Good for:**
- Identical repeated queries
- Development and testing
- Read-heavy applications
- Low-latency requirements

❌ **Not ideal for:**
- Unique queries every time
- Real-time dynamic data
- Large variation in parameters

### When to Use Provider Prompt Caching

✅ **Good for:**
- Large document Q&A
- Codebase analysis
- Multi-turn conversations with context
- Repeated analysis of same content

❌ **Not ideal for:**
- Small prompts (< 1024 tokens)
- Single-use contexts
- Frequently changing content

### Optimization Tips

1. **Set appropriate TTL**: Balance freshness vs. cache hits
   - Short TTL (60-300s): Dynamic content
   - Long TTL (3600s+): Static reference material

2. **Monitor cache stats**: Track hit rate and adjust strategy
   ```python
   stats = get_cache_stats()
   hit_rate = stats['total_hits'] / max(stats['size'], 1)
   ```

3. **Use cache control strategically**: Only cache large, reusable contexts
   - Mark system prompts with large documents
   - Don't cache frequently changing content

4. **Combine caching strategies**: Use both response and provider caching

5. **Clear cache when needed**: Clear after context changes
   ```python
   clear_cache()  # Clear when underlying data changes
   ```

---

## Troubleshooting

### Cache Not Working

**Issue**: Responses are not being cached

**Solutions**:
- Ensure parameters are identical (temperature, messages, model)
- Check if streaming is disabled (streaming responses aren't cached)
- Verify cache TTL hasn't expired

### High Cache Miss Rate

**Issue**: Low cache hit rate

**Solutions**:
- Increase TTL if content doesn't change frequently
- Normalize input parameters (e.g., consistent temperature)
- Check if queries are truly repeated

### Provider Cache Not Applied

**Issue**: No cache_creation_tokens or cache_read_tokens

**Solutions**:
- Verify model supports caching: `provider.supports_caching(model)`
- Ensure `cache_control` is set on messages
- Check that context is large enough (typically 1024+ tokens)
- Confirm API key has caching enabled (provider-specific)

---

## Performance Metrics

### Response Cache Performance

- **Cache hit latency**: < 1ms (in-memory lookup)
- **Memory overhead**: ~1KB per cached response
- **Thread safety**: Full thread-safe with locks
- **Eviction policy**: LRU (Least Recently Used)

### Provider Cache Performance

- **First request latency**: +10-20ms (cache write)
- **Subsequent requests latency**: -30-50ms (cache read)
- **Cache lifetime**: Varies by provider (typically 5 minutes)
- **Cost reduction**: Up to 90% for cached tokens

---

## Version History

- **v0.1.0** (2026-01-30): Initial caching implementation
  - Response caching with TTL and size limits
  - Provider prompt caching for OpenAI, Anthropic, Google
  - Cache control API
  - Cost tracking with breakdown
  - Comprehensive test coverage (20 tests)

---

For more information, see:
- [StratifyAI Documentation](../README.md)
- [Technical Approach](stratifyai-technical-approach.md)
- [API Examples](../examples/)
