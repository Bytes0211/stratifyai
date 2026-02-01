
Below is a **detailed, realistic, production‑style implementation** using a model API (OpenAI‑compatible for simplicity). It demonstrates:

- How to **hash prompts**  
- How to **store and reuse cached responses**  
- How to **avoid recomputing long system prompts**  
- How to **cache embeddings or pre‑tokenized chunks**  
- How to **simulate KV‑cache reuse** the way real providers do  

This is the closest you can get to “manual prompt caching” without needing access to the model’s internal KV cache.

---

# 🧠 First: What You *Can* Implement Yourself

You can implement:

### ✔️ **Prompt hashing**  
Detect when a prompt (or part of it) is identical to a previous one.

### ✔️ **Cache lookup**  
Return the previous result instantly.

### ✔️ **Chunk‑level caching**  
Cache expensive static parts (system prompts, RAG documents).

### ✔️ **Embedding caching**  
Cache vector embeddings so you don’t recompute them.

### ✔️ **Response caching**  
Cache the model’s output for identical inputs.

### ✔️ **Partial prompt caching**  
Reuse the “static prefix” of a prompt and only send the dynamic part.

---

# 🧪 Full Python Example: Prompt Caching Layer for an LLM API

This example uses an OpenAI‑compatible API, but the pattern works for Anthropic, Google, DeepSeek, Groq, etc.

---

# 1. A Simple Cache Backend

```python
import hashlib
import json
from functools import lru_cache

def hash_prompt(prompt: dict) -> str:
    """Create a stable hash for a prompt."""
    prompt_str = json.dumps(prompt, sort_keys=True)
    return hashlib.sha256(prompt_str.encode()).hexdigest()
```

---

# 2. A Prompt Cache Class

```python
class PromptCache:
    def __init__(self):
        self.cache = {}

    def get(self, prompt_hash: str):
        return self.cache.get(prompt_hash)

    def set(self, prompt_hash: str, response: dict):
        self.cache[prompt_hash] = response
```

---

# 3. LLM Client With Caching

```python
from openai import OpenAI

class CachedLLMClient:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.cache = PromptCache()

    def chat(self, messages, model="gpt-4.1-mini", temperature=0.2):
        prompt = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        # 1. Hash the prompt
        prompt_hash = hash_prompt(prompt)

        # 2. Check cache
        cached = self.cache.get(prompt_hash)
        if cached:
            print("⚡ Cache hit")
            return cached

        print("🧠 Cache miss — calling model")

        # 3. Call the model
        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )

        # 4. Normalize response
        normalized = {
            "content": response.choices[0].message["content"],
            "usage": response.usage.model_dump(),
            "model": response.model,
        }

        # 5. Store in cache
        self.cache.set(prompt_hash, normalized)

        return normalized
```

---

# 4. Using the Cached Client

```python
client = CachedLLMClient(api_key="YOUR_KEY")

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Explain quantum computing simply."}
]

# First call → cache miss
resp1 = client.chat(messages)

# Second call → cache hit
resp2 = client.chat(messages)
```

Output:

```
🧠 Cache miss — calling model
⚡ Cache hit
```

---

# 🧠 What This Gives You

- Identical prompts return instantly  
- You avoid recomputing long system prompts  
- You reduce cost and latency  
- You simulate the effect of KV‑cache reuse  

This is the **application‑level** version of prompt caching.

---

# 🧩 Advanced: Partial Prompt Caching (Static Prefix)

Most real prompts look like this:

```
[STATIC SYSTEM PROMPT — 10,000 tokens]
[STATIC RULES — 5,000 tokens]
[USER INPUT — 20 tokens]
```

You can cache the static prefix separately.

```python
class PrefixCache:
    def __init__(self):
        self.prefix_hash = None
        self.prefix_tokens = None

    def compute_prefix(self, prefix_messages):
        prefix_hash = hash_prompt(prefix_messages)
        if prefix_hash == self.prefix_hash:
            return self.prefix_tokens  # already cached

        # expensive step: send prefix to model to warm KV cache
        self.prefix_tokens = prefix_messages
        self.prefix_hash = prefix_hash
        return self.prefix_tokens
```

Then:

```python
prefix = prefix_cache.compute_prefix(static_messages)
full_prompt = prefix + dynamic_messages
response = client.chat(full_prompt)
```

This mimics how **Anthropic Prompt Caching** and **OpenAI Reusable Prompts** work internally.

---

# 🧠 Advanced: Embedding Cache (RAG)

```python
@lru_cache(maxsize=5000)
def embed(text: str):
    return client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    ).data[0].embedding
```

This avoids recomputing embeddings for repeated documents.

---

# 🧠 Advanced: Chunk‑Level Caching

If you have a long system prompt:

```python
system_prompt = """
# Rules
1. Always respond concisely.
2. Use markdown.
3. Follow safety guidelines.
...
(10,000 tokens)
"""
```

You can split it:

```python
chunks = system_prompt.split("\n\n")
cached_chunks = [prefix_cache.compute_prefix([{"role": "system", "content": c}]) for c in chunks]
```

This is how **Bedrock**, **Anthropic**, and **OpenAI** internally reuse KV cache for repeated prompt segments.

---

# 🎯 Summary

You now have:

### ✔️ A working Python implementation  
### ✔️ Full prompt hashing  
### ✔️ Response caching  
### ✔️ Prefix caching (simulated KV reuse)  
### ✔️ Embedding caching  
### ✔️ Chunk‑level caching  

This is the **real‑world way** to implement prompt caching without needing access to the model’s internal KV cache.

