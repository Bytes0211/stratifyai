# Prompt Caching Quick Reference

Fast reference guide for using prompt caching in StratifyAI.

---

## Response Caching (In-Memory)

### Basic Usage
```python
from stratifyai import LLMClient, Message

client = LLMClient()

# Second identical call uses cache automatically
response = client.chat(
    model="gpt-4.1-mini",
    messages=[Message(role="user", content="Hello")],
    temperature=0.7
)
```

### Custom Cache
```python
from stratifyai import ResponseCache, cache_response

cache = ResponseCache(ttl=600, max_size=100)

@cache_response(ttl=600, cache_instance=cache)
def cached_chat(**kwargs):
    return client.chat(**kwargs)
```

### Cache Stats
```python
from stratifyai import get_cache_stats, clear_cache

stats = get_cache_stats()
print(f"Size: {stats['size']}, Hits: {stats['total_hits']}")

clear_cache()  # Clear when needed
```

---

## Provider Prompt Caching (OpenAI/Anthropic/Google)

### With Cache Control
```python
from stratifyai import LLMClient, Message

# Mark large content for provider caching
messages = [
    Message(
        role="system",
        content=large_document,
        cache_control={"type": "ephemeral"}  # Enable caching
    ),
    Message(role="user", content="Question")
]

response = client.chat(model="gpt-4.1-mini", messages=messages)

# Check cache usage
print(f"Cache write: {response.usage.cache_creation_tokens}")
print(f"Cache read: {response.usage.cache_read_tokens}")
print(f"Cost: ${response.usage.cost_usd:.4f}")
```

### Check Support
```python
from stratifyai.providers.openai import OpenAIProvider

provider = OpenAIProvider(api_key="key")
if provider.supports_caching("gpt-4.1-mini"):
    print("Caching supported!")
```

---

## Cost Breakdown

### Cache Costs
- **Cache Write**: +25% of input cost (first request)
- **Cache Read**: -90% of input cost (subsequent requests)
- **Break-even**: 2 requests with same context

### Example: 50K tokens
```
Without caching (10 calls): $0.075
With caching (10 calls):    $0.0166
Savings:                    $0.0584 (78%)
```

---

## Supported Models

### OpenAI
✅ gpt-5, gpt-5-mini, gpt-4.1, gpt-4.1-mini  
❌ o1, o1-mini, o3-mini (reasoning models)

### Anthropic
✅ claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus

### Google
✅ gemini-2.5-pro, gemini-2.5-flash

### Others
❌ DeepSeek, Groq, Grok, Ollama (not supported)

---

## Common Patterns

### Pattern 1: Dev/Test Caching
```python
from stratifyai import LLMClient, cache_response

@cache_response(ttl=3600)  # 1 hour
def dev_query(prompt):
    return client.chat(
        model="gpt-4.1-mini",
        messages=[Message(role="user", content=prompt)]
    )
```

### Pattern 2: Document Q&A
```python
# Reusable context
doc = Message(
    role="system",
    content=document,
    cache_control={"type": "ephemeral"}
)

# Multiple queries with same context
for question in questions:
    response = client.chat(
        model="gpt-4.1-mini",
        messages=[doc, Message(role="user", content=question)]
    )
```

### Pattern 3: Combined Caching
```python
from stratifyai import ResponseCache, cache_response

cache = ResponseCache(ttl=600)

@cache_response(cache_instance=cache)
def smart_query(context, question):
    messages = [
        Message(
            role="system",
            content=context,
            cache_control={"type": "ephemeral"}
        ),
        Message(role="user", content=question)
    ]
    return client.chat(model="gpt-4.1-mini", messages=messages)
```

---

## Troubleshooting

### Cache Not Working?
1. Check parameters are identical
2. Disable streaming: `stream=False`
3. Verify TTL hasn't expired

### Provider Cache Not Applied?
1. Check model supports caching
2. Ensure `cache_control` is set
3. Context must be 1024+ tokens

### High Costs?
1. Monitor cache hits: `get_cache_stats()`
2. Use provider caching for large contexts
3. Combine both caching strategies

---

## API Quick Reference

```python
# Response caching
from stratifyai import (
    ResponseCache,         # Cache class
    cache_response,        # Decorator
    get_cache_stats,       # Get stats
    clear_cache,          # Clear cache
    generate_cache_key    # Generate key
)

# Usage tracking
response.usage.cached_tokens           # Total cached
response.usage.cache_creation_tokens   # Tokens written
response.usage.cache_read_tokens       # Tokens read
response.usage.cost_breakdown          # Cost details

# Message caching
Message(
    role="system",
    content="...",
    cache_control={"type": "ephemeral"}
)
```

---

## See Also

- [Full Documentation](CACHING.md)
- [Examples](../examples/caching_examples.py)
- [Implementation Summary](caching-implementation-summary.md)
