Absolutely, Steven — here is a **fully rewritten, polished, documentation‑grade version** of your entire caching guide. It keeps all the technical accuracy of your original file but improves clarity, structure, flow, and developer experience. It now reads like something you’d expect from a mature open‑source framework.

Everything is rewritten from scratch — no copy/paste — but all features, examples, and concepts remain intact.

---

# **StratumAI Prompt Caching: Architecture, Usage, and Cost Optimization**

### A complete guide to response caching and provider‑level prompt caching for faster, cheaper, and more efficient LLM workloads

Efficient caching is one of the most impactful ways to reduce latency and control costs in large‑scale LLM applications. StratumAI provides a dual‑layer caching system that accelerates repeated queries, optimizes multi‑turn workflows, and dramatically reduces the cost of working with large context windows.

This guide explains how StratumAI’s caching system works, how to use it effectively, and how to measure the performance and cost benefits it provides.

---

# **1. Overview**

StratumAI implements two complementary caching mechanisms:

### **1. Response Caching (StratumAI‑level)**
A thread‑safe, in‑memory cache that stores **complete LLM responses**.  
If a request is repeated with identical parameters, StratumAI returns the cached response instantly — no provider call required.

### **2. Provider Prompt Caching (Model‑level)**
Native support for provider‑specific caching features (OpenAI, Anthropic, Google).  
This allows large context blocks to be cached *inside the provider*, reducing token costs by up to **90%** on subsequent requests.

Together, these two layers provide:

- Lower latency  
- Lower cost  
- Higher throughput  
- Better performance for RAG, multi‑turn chat, and large‑document analysis  

---

# **2. Response Caching**

Response caching stores full LLM responses in memory and returns them for identical requests. This is ideal for repeated queries, static prompts, and read‑heavy workloads.

## **Key Features**

- **Thread‑safe in‑memory cache**
- **Configurable TTL** (default: 3600 seconds)
- **Oldest-entry eviction** when max size is reached
- **Cache hit statistics**
- **Decorator support** for easy integration

## **Basic Example**

```python
from llm_abstraction import LLMClient, Message

client = LLMClient()

# First call → real API request
response1 = client.chat(
    model="gpt-4.1-mini",
    messages=[Message(role="user", content="What is 2+2?")],
    temperature=0.7,
)

# Second call → served from cache
response2 = client.chat(
    model="gpt-4.1-mini",
    messages=[Message(role="user", content="What is 2+2?")],
    temperature=0.7,
)
```

## **Custom Cache Configuration**

```python
from llm_abstraction import ResponseCache, cache_response, LLMClient

custom_cache = ResponseCache(ttl=300, max_size=100)
client = LLMClient()

@cache_response(ttl=300, cache_instance=custom_cache)
def cached_chat(**kwargs):
    return client.chat(**kwargs)
```

## **Cache Management**

```python
from llm_abstraction import get_cache_stats, clear_cache

stats = get_cache_stats()
clear_cache()
```

---

# **3. Provider Prompt Caching**

Provider prompt caching allows large context blocks to be cached *inside the model provider*, dramatically reducing token costs for repeated use of the same context.

This is ideal for:

- Large documents  
- Codebases  
- Knowledge base chunks  
- Multi‑turn conversations with static context  

## **Provider Support**

| Provider | Supported | Cache Write Cost | Cache Read Cost | Notes |
|---------|-----------|------------------|-----------------|-------|
| OpenAI | Yes | +25% | -90% | gpt‑4.1+, gpt‑5 |
| Anthropic | Yes | +25% | -90% | Claude 3+ |
| Google | Yes | +25% | -90% | Gemini 2.5+ |
| DeepSeek | No | — | — | Not supported |
| Groq | No | — | — | Not supported |
| Grok | No | — | — | Not supported |
| OpenRouter | Varies | Varies | Varies | Depends on underlying model |
| Ollama | No | — | — | Local models |

## **How It Works**

1. **First request**  
   Provider stores the marked context (cache write).

2. **Subsequent requests**  
   Provider reuses the cached context (cache read).

3. **Cost savings**  
   Cache reads are up to **90% cheaper** than normal input tokens.

## **Example: Caching a Large Document**

```python
from llm_abstraction import LLMClient, Message

client = LLMClient()

large_doc = "[50,000+ token document]"

messages = [
    Message(
        role="system",
        content=large_doc,
        cache_control={"type": "ephemeral"}  # Enable provider caching
    ),
    Message(role="user", content="Summarize the key points.")
]

response1 = client.chat(model="gpt-4.1-mini", messages=messages)
```

Subsequent calls reuse the cached context:

```python
messages[1] = Message(role="user", content="What challenges are discussed?")
response2 = client.chat(model="gpt-4.1-mini", messages=messages)
```

---

# **4. Cost Savings**

## **Response Caching Savings**

- Cached responses cost **$0**  
- Ideal for repeated identical queries  

Example:

| Scenario | API Calls | Cost |
|----------|-----------|------|
| Without caching | 5 | $0.0015 |
| With caching | 3 | $0.0009 |

**Savings: 40%**

---

## **Provider Prompt Caching Savings**

Example: 50,000‑token document with GPT‑4.1‑mini

| Scenario | Cost |
|----------|------|
| First call (cache write) | $0.0094 |
| Subsequent calls (cache read) | $0.0008 |

After 10 calls:

- Without caching: **$0.075**
- With caching: **$0.0166**

**Savings: 78%**

---

## **Combined Strategy**

Use both caching layers for maximum efficiency:

```python
@cache_response(ttl=600)
def cached_chat(**kwargs):
    return client.chat(**kwargs)
```

---

# **5. API Reference**

## **ResponseCache**

```python
class ResponseCache:
    def __init__(self, ttl=3600, max_size=1000): ...
    def get(self, key): ...
    def set(self, key, response): ...
    def clear(self): ...
    def get_stats(self): ...
    def get_entries(self): ...  # Returns detailed info about cached entries
```

## **cache_response Decorator**

```python
@cache_response(ttl=600)
def my_chat(**kwargs):
    return client.chat(**kwargs)
```

## **Cache Control on Messages**

```python
Message(
    role="system",
    content="Large context",
    cache_control={"type": "ephemeral"}
)
```

## **Usage Model Extensions**

```python
@dataclass
class Usage:
    cached_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    reasoning_tokens: int = 0  # For reasoning models (o1/o3)
    cost_breakdown: Optional[dict] = None
```

---

# **6. Best Practices**

### **Use Response Caching When:**
- Queries repeat frequently  
- Prompts are static  
- You want instant responses  

### **Use Provider Caching When:**
- Context is large (10k–100k tokens)  
- Multiple questions reference the same document  
- You’re running multi‑turn workflows  

### **Avoid Caching When:**
- Data is sensitive  
- Content changes frequently  
- Prompts are highly dynamic  

---

# **7. Troubleshooting**

### **Cache Misses**
- Ensure parameters match exactly  
- Streaming responses are not cached  
- TTL may have expired  

### **Provider Cache Not Used**
- Model may not support caching  
- `cache_control` missing  
- Context too small (<1024 tokens)  

---

# **8. Performance Metrics**

### **Response Cache**
- Latency: <1ms  
- Memory: ~1KB per entry  
- Eviction: Oldest-entry (FIFO)

### **Provider Cache**
- Write: +10–20ms  
- Read: -30–50ms  
- Lifetime: ~5 minutes (provider‑controlled)  

---

# **9. Version History**

**v0.1.0 (2026‑01‑30)**  
- Initial caching system  
- Response caching with TTL + LRU  
- Provider caching for OpenAI, Anthropic, Google  
- Cache control API  
- Cost breakdown support  
- 20+ tests  

---
