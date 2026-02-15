# StratifyAI API Reference

Complete API documentation for StratifyAI multi-provider LLM abstraction module.

**Version:** 1.0.0  
**Last Updated:** February 1, 2026

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [LLMClient](#llmclient)
3. [Data Models](#data-models)
4. [Providers](#providers)
5. [Router](#router)
6. [Cost Tracking](#cost-tracking)
7. [Caching](#caching)
8. [Error Handling](#error-handling)
9. [CLI Reference](#cli-reference)

---

## Quick Start

### Installation

```bash
# Clone repository
git clone <repo-url>
cd stratifyai

# Install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Basic Usage

**Async (Recommended):**
```python
import asyncio
from stratifyai import LLMClient
from stratifyai.models import Message, ChatRequest, ChatResponse

async def main():
    client = LLMClient()
    
    request = ChatRequest(
        model="gpt-4o-mini",
        messages=[Message(role="user", content="Hello!")]
    )
    
    response: ChatResponse = await client.chat_completion(request)
    
    print(response.content)
    print(f"Cost: ${response.usage.cost_usd:.6f}")
    print(f"Latency: {response.latency_ms:.0f}ms")

asyncio.run(main())
```

**Sync (CLI/Scripts):**
```python
from stratifyai import LLMClient
from stratifyai.models import Message, ChatRequest, ChatResponse

client = LLMClient()

request = ChatRequest(
    model="gpt-4o-mini",
    messages=[Message(role="user", content="Hello!")]
)

response: ChatResponse = client.chat_completion_sync(request)

print(response.content)
print(f"Cost: ${response.usage.cost_usd:.6f}")
```

---

## LLMClient

The unified client for accessing all LLM providers.

### Class: `LLMClient`

**Location:** `llm_abstraction/client.py`

#### Constructor

```python
LLMClient(
    api_keys: Optional[Dict[str, str]] = None,
    default_temperature: float = 0.7,
    default_max_tokens: Optional[int] = None
)
```

**Parameters:**
- `api_keys` (dict, optional): Provider API keys. If not provided, reads from environment variables.
- `default_temperature` (float): Default temperature for all requests (default: 0.7)
- `default_max_tokens` (int, optional): Default max tokens for responses

**Environment Variables:**
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `GOOGLE_API_KEY` - Google Gemini API key
- `DEEPSEEK_API_KEY` - DeepSeek API key
- `GROQ_API_KEY` - Groq API key
- `XAI_API_KEY` - Grok (X.AI) API key
- `OPENROUTER_API_KEY` - OpenRouter API key
- `OLLAMA_BASE_URL` - Ollama server URL (default: http://localhost:11434)

#### Methods

##### `chat_completion()` (Async)

Send an async chat completion request.

```python
async def chat_completion(
    request: ChatRequest
) -> ChatResponse
```

**Parameters:**
- `request` (ChatRequest): Chat completion request with model, messages, temperature, etc.

**Returns:** `ChatResponse` object

**Example:**
```python
import asyncio
from stratifyai.models import Message, ChatRequest, ChatResponse

request = ChatRequest(
    model="gpt-4o-mini",
    messages=[
        Message(role="system", content="You are a helpful assistant."),
        Message(role="user", content="Explain quantum computing")
    ],
    temperature=0.7,
    max_tokens=500
)

response: ChatResponse = await client.chat_completion(request)
print(response.content)
```

##### `chat_completion_sync()` (Sync)

Synchronous wrapper for chat completion (for CLI/scripts).

```python
def chat_completion_sync(
    request: ChatRequest
) -> ChatResponse
```

**Parameters:** Same as `chat_completion()`

**Returns:** `ChatResponse` object

**Example:**
```python
request = ChatRequest(
    model="gpt-4o-mini",
    messages=[Message(role="user", content="Hello!")]
)

response: ChatResponse = client.chat_completion_sync(request)
print(response.content)
```

##### `chat_completion_stream()` (Async)

Stream async chat completion responses.

```python
async def chat_completion_stream(
    request: ChatRequest
) -> AsyncIterator[ChatResponse]
```

**Parameters:**
- `request` (ChatRequest): Chat completion request with stream=True

**Returns:** AsyncIterator yielding `ChatResponse` chunks

**Example:**
```python
import asyncio

request = ChatRequest(
    model="gpt-4o-mini",
    messages=[Message(role="user", content="Write a poem")],
    stream=True
)

async for chunk in client.chat_completion_stream(request):
    print(chunk.content, end="", flush=True)
```

##### `chat_completion_stream_sync()` (Sync)

Synchronous streaming wrapper.

```python
def chat_completion_stream_sync(
    request: ChatRequest
) -> Iterator[ChatResponse]
```

**Parameters:** Same as `chat_completion_stream()`

**Returns:** Iterator yielding `ChatResponse` chunks

**Example:**
```python
request = ChatRequest(
    model="gpt-4o-mini",
    messages=[Message(role="user", content="Write a story")],
    stream=True
)

for chunk in client.chat_completion_stream_sync(request):
    print(chunk.content, end="", flush=True)
```

##### `list_models()`

List available models for a provider.

```python
list_models(provider: str) -> List[str]
```

**Parameters:**
- `provider` (str): Provider name (openai, anthropic, google, etc.)

**Returns:** List of model identifiers

**Example:**
```python
models = client.list_models("openai")
print(models)  # ['gpt-4.1', 'gpt-4.1-mini', 'o1', ...]
```

##### `get_provider()`

Get provider instance for a model.

```python
get_provider(model: str) -> BaseProvider
```

**Parameters:**
- `model` (str): Model identifier

**Returns:** Provider instance implementing `BaseProvider`

**Example:**
```python
provider = client.get_provider("gpt-4o-mini")
print(provider.name)  # 'openai'
```

---

## Data Models

### Message

Represents a single chat message.

**Location:** `llm_abstraction/models.py`

```python
@dataclass
class Message:
    role: str                           # "system", "user", or "assistant"
    content: str                        # Message text
    name: Optional[str] = None          # Speaker name
    cache_control: Optional[dict] = None  # Cache control for prompt caching
```

**Example:**
```python
from stratifyai.models import Message

msg = Message(
    role="user",
    content="Explain photosynthesis",
    cache_control={"type": "ephemeral"}  # For Anthropic prompt caching
)
```

### ChatRequest

Chat completion request parameters.

```python
@dataclass
class ChatRequest:
    model: str
    messages: List[Message]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    top_p: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop: Optional[List[str]] = None
```

### ChatResponse

Chat completion response.

```python
@dataclass
class ChatResponse:
    content: str                        # Response text
    model: str                          # Model used
    provider: str                       # Provider name
    usage: Usage                        # Token usage and cost
    latency_ms: float                   # Response latency in milliseconds
    finish_reason: Optional[str] = None # "stop", "length", etc.
    created_at: Optional[datetime] = None
```

**Example:**
```python
request = ChatRequest(
    model="gpt-4o-mini",
    messages=[Message(role="user", content="Hello!")]
)

response: ChatResponse = await client.chat_completion(request)
print(f"Content: {response.content}")
print(f"Model: {response.model}")
print(f"Provider: {response.provider}")
print(f"Tokens: {response.usage.total_tokens}")
print(f"Cost: ${response.usage.cost_usd:.6f}")
print(f"Latency: {response.latency_ms:.0f}ms")
```

### Usage

Token usage and cost information.

```python
@dataclass
class Usage:
    prompt_tokens: int                  # Input tokens
    completion_tokens: int              # Output tokens
    total_tokens: int                   # Total tokens
    cost_usd: float                     # Total cost in USD
    
    # Prompt caching fields
    cached_tokens: int = 0              # Tokens retrieved from cache
    cache_creation_tokens: int = 0      # Tokens written to cache
    cache_read_tokens: int = 0          # Tokens read from cache
    cost_breakdown: Optional[Dict[str, float]] = None  # Detailed cost breakdown
```

---

## Providers

All providers implement the `BaseProvider` abstract interface.

### Supported Providers

| Provider | Models | Notes |
|----------|--------|-------|
| OpenAI | GPT-4.1, GPT-4.1-mini, o1, o3-mini, GPT-5 | Full support, prompt caching |
| Anthropic | Claude Sonnet 4/3.5, Haiku 4, Opus 4 | Messages API, prompt caching |
| Google | Gemini 2.5 Flash, Pro, Ultra | OpenAI-compatible, prompt caching |
| DeepSeek | DeepSeek Chat, Reasoner | OpenAI-compatible |
| Groq | Llama 3.3, 3.1, Mixtral | Ultra-fast inference |
| Grok | Grok 3, 2.5 | X.AI models |
| OpenRouter | 100+ models | Unified access to multiple providers |
| Ollama | All local models | Local deployment |

### BaseProvider Interface

**Location:** `llm_abstraction/providers/base.py`

All providers are async-first and use native SDK async clients.

```python
class BaseProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """Send async chat completion request."""
        pass
    
    @abstractmethod
    async def chat_stream(self, request: ChatRequest) -> AsyncIterator[ChatResponse]:
        """Stream async chat completion."""
        pass
    
    @abstractmethod
    def list_models(self) -> List[str]:
        """List available models."""
        pass
```

### Provider-Specific Features

#### OpenAI Provider

**Prompt Caching:**
```python
import asyncio
from stratifyai import LLMClient
from stratifyai.models import Message, ChatRequest

# Automatic prompt caching for long contexts
request = ChatRequest(
    model="gpt-4o-mini",
    messages=[
        Message(role="system", content=long_context),  # Cached automatically if >1024 tokens
        Message(role="user", content="What is the main theme?")
    ]
)

response = await client.chat_completion(request)
print(f"Cached tokens: {response.usage.cached_tokens}")
```

#### Anthropic Provider

**Prompt Caching:**
```python
import asyncio
from stratifyai import LLMClient
from stratifyai.models import Message, ChatRequest

# Explicit cache control for Claude
messages = [
    Message(
        role="user",
        content=long_document,
        cache_control={"type": "ephemeral"}  # Cache this message
    ),
    Message(role="user", content="Summarize this")
]

request = ChatRequest(
    model="claude-sonnet-4-5",  # Claude Sonnet 4.5
    messages=messages
)

response = await client.chat_completion(request)
print(f"Cache read tokens: {response.usage.cache_read_tokens}")
print(f"Cost savings: ${response.usage.cost_breakdown.get('cache_savings', 0):.6f}")
```

#### Ollama Provider

**Local Deployment:**
```python
import asyncio
from stratifyai import LLMClient
from stratifyai.models import Message, ChatRequest

# Requires Ollama running locally
# Start server: ollama serve (default: http://localhost:11434)

request = ChatRequest(
    model="llama3.3",
    messages=[Message(role="user", content="Hello")]
)

response = await client.chat_completion(request)
print(response.content)
```

---

## Router

Intelligent model selection based on prompt complexity.

### Class: `Router`

**Location:** `llm_abstraction/router.py`

#### Constructor

```python
Router(
    client: LLMClient,
    default_strategy: RoutingStrategy = RoutingStrategy.HYBRID,
    preferred_providers: Optional[List[str]] = None,
    excluded_providers: Optional[List[str]] = None
)
```

**Parameters:**
- `client` (LLMClient): LLM client instance
- `default_strategy` (RoutingStrategy): Default routing strategy
- `preferred_providers` (list, optional): Providers to prefer
- `excluded_providers` (list, optional): Providers to exclude

#### Routing Strategies

```python
class RoutingStrategy(Enum):
    COST = "cost"           # Minimize cost
    QUALITY = "quality"     # Maximize quality
    LATENCY = "latency"     # Minimize latency
    HYBRID = "hybrid"       # Balance based on complexity
```

#### Methods

##### `route()` (Async)

Select optimal model and send async request.

```python
async def route(
    prompt: str,
    strategy: Optional[RoutingStrategy] = None,
    constraints: Optional[RoutingConstraints] = None,
    **kwargs
) -> ChatResponse
```

**Parameters:**
- `prompt` (str): User prompt/query
- `strategy` (RoutingStrategy, optional): Override default strategy
- `constraints` (RoutingConstraints, optional): Additional constraints
- `**kwargs`: Passed to underlying chat call (temperature, max_tokens, etc.)

**Returns:** `ChatResponse` with selected model

**Example:**
```python
import asyncio
from stratifyai import LLMClient, Router, RoutingStrategy
from stratifyai.router import RoutingConstraints

client = LLMClient()
router = Router(client, default_strategy=RoutingStrategy.HYBRID)

# Simple routing (cheapest model)
response = await router.route(
    prompt="What is 2+2?",
    strategy=RoutingStrategy.COST
)
print(f"Selected model: {response.model}")
print(f"Cost: ${response.usage.cost_usd:.6f}")

# Complex task with constraints
response = await router.route(
    prompt="Analyze this complex dataset...",
    strategy=RoutingStrategy.QUALITY,
    constraints=RoutingConstraints(
        max_cost_per_1k_tokens=0.01,
        min_context_window=32000,
        capabilities=["reasoning"]
    ),
    temperature=0.3
)
print(f"Selected: {response.model} via {response.provider}")
```

##### `route_sync()` (Sync)

Synchronous wrapper for routing.

```python
def route_sync(
    prompt: str,
    strategy: Optional[RoutingStrategy] = None,
    constraints: Optional[RoutingConstraints] = None,
    **kwargs
) -> ChatResponse
```

**Example:**
```python
from stratifyai import LLMClient, Router, RoutingStrategy

client = LLMClient()
router = Router(client)

response = router.route_sync(
    prompt="Explain relativity",
    strategy=RoutingStrategy.HYBRID
)
print(response.content)
```

##### `analyze_complexity()`

Analyze prompt complexity (0.0-1.0).

```python
analyze_complexity(messages: List[Dict[str, str]]) -> float
```

**Complexity Factors:**
- **Reasoning keywords (40%)**: analyze, explain, prove, calculate
- **Length (20%)**: Longer prompts = higher complexity
- **Technical content (20%)**: Code blocks, technical terms
- **Multi-turn (10%)**: Conversation history
- **Mathematical (10%)**: Equations, formulas

**Example:**
```python
complexity = router.analyze_complexity([
    {"role": "user", "content": "Prove that sqrt(2) is irrational"}
])
print(f"Complexity: {complexity:.2f}")  # ~0.75 (high complexity)
```

##### `get_model_info()`

Get metadata for a model.

```python
get_model_info(model_name: str) -> Optional[ModelMetadata]
```

**Returns:** `ModelMetadata` with quality score, cost, latency, context window

---

## Cost Tracking

Track and manage LLM API costs.

### Class: `CostTracker`

**Location:** `llm_abstraction/cost_tracker.py`

#### Constructor

```python
CostTracker(
    budget_limit: Optional[float] = None,
    alert_threshold: float = 0.8
)
```

**Parameters:**
- `budget_limit` (float, optional): Maximum spend in USD
- `alert_threshold` (float): Alert when % of budget reached (default: 0.8)

#### Methods

##### `record_call()`

Record an LLM API call.

```python
record_call(
    model: str,
    provider: str,
    usage: Usage,
    metadata: Optional[Dict[str, Any]] = None
) -> None
```

**Example:**
```python
from stratifyai import CostTracker

tracker = CostTracker(budget_limit=10.0)

response = client.chat(model="gpt-4o-mini", messages=[...])
tracker.record_call(
    model=response.model,
    provider=response.provider,
    usage=response.usage
)
```

##### `get_summary()`

Get cost summary statistics.

```python
get_summary() -> Dict[str, Any]
```

**Returns:** Dictionary with total_cost, total_calls, by_provider, by_model

**Example:**
```python
summary = tracker.get_summary()
print(f"Total cost: ${summary['total_cost']:.4f}")
print(f"Total calls: {summary['total_calls']}")
print(f"By provider: {summary['by_provider']}")
```

##### `check_budget()`

Check if budget limit is exceeded.

```python
check_budget() -> Tuple[bool, float]
```

**Returns:** (within_budget: bool, remaining: float)

**Example:**
```python
within_budget, remaining = tracker.check_budget()
if not within_budget:
    print(f"Budget exceeded! Overspent by ${abs(remaining):.2f}")
```

---

## Caching

Response caching and provider-level prompt caching.

### ResponseCache

LRU cache for LLM responses.

**Location:** `llm_abstraction/caching.py`

#### Constructor

```python
ResponseCache(
    max_size: int = 1000,
    ttl: int = 3600  # seconds
)
```

#### Usage

```python
from stratifyai.caching import ResponseCache

cache = ResponseCache(max_size=500, ttl=1800)

# Cache key from messages
cache_key = cache.generate_key(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
    temperature=0.7
)

# Check cache
cached_response = cache.get(cache_key)
if cached_response:
    print("Cache hit!")
else:
    response = client.chat(...)
    cache.set(cache_key, response)
```

### Decorator Usage

```python
from stratifyai.caching import cache_response

@cache_response(ttl=1800)
def ask_llm(question: str) -> str:
    response = client.chat(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}]
    )
    return response.content

# First call - API request
answer = ask_llm("What is AI?")  # Cache miss

# Second call - cached
answer = ask_llm("What is AI?")  # Cache hit (<1ms)
```

### Prompt Caching

Provider-level prompt caching for repeated long contexts.

**Supported Providers:**
- OpenAI (automatic for contexts >1024 tokens)
- Anthropic (explicit cache_control)
- Google (automatic)

**Cost Savings:**
- Cache writes: 25% of normal cost
- Cache reads: 10% of normal cost
- **Total savings: up to 90%**

**Example:**
```python
# Anthropic explicit caching
from stratifyai.models import Message

long_doc = "..." * 10000  # Large document

messages = [
    Message(
        role="user",
        content=long_doc,
        cache_control={"type": "ephemeral"}  # Cache this
    ),
    Message(role="user", content="Summarize")
]

response = client.chat(model="claude-sonnet-4-5-20250929", messages=messages)

# First call: cache_creation_tokens charged
print(f"Cache creation: {response.usage.cache_creation_tokens}")

# Second call with same doc: cache_read_tokens (90% savings)
response2 = client.chat(model="claude-sonnet-4-5-20250929", messages=messages)
print(f"Cache read: {response2.usage.cache_read_tokens}")
print(f"Cost saved: ${response.usage.cost_usd - response2.usage.cost_usd:.4f}")
```

See [CACHING.md](CACHING.md) for complete documentation.

---

## Error Handling

Custom exception hierarchy for robust error handling.

**Location:** `llm_abstraction/exceptions.py`

### Exception Hierarchy

```
LLMException (base)
├── ProviderException
│   ├── ProviderNotFoundError
│   ├── ModelNotFoundError
│   └── ProviderAPIError
├── AuthenticationException
├── RateLimitException
├── InvalidRequestException
├── BudgetExceededException
├── CacheMissException
└── RouterException
```

### Usage

```python
from stratifyai.exceptions import (
    RateLimitException,
    BudgetExceededException,
    ModelNotFoundError
)

try:
    response = client.chat(model="invalid-model", messages=[...])
except ModelNotFoundError as e:
    print(f"Model not found: {e}")
except RateLimitException as e:
    print(f"Rate limited: {e}. Retry after {e.retry_after}s")
except BudgetExceededException as e:
    print(f"Budget exceeded: {e}")
```

### Retry Logic

Automatic retry with exponential backoff.

```python
from stratifyai.retry import with_retry, RetryConfig

config = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0,
    fallback_models=["gpt-4o-mini", "claude-haiku-4"]
)

@with_retry(config)
def robust_chat(messages):
    return client.chat(model="gpt-4.1", messages=messages)

# Automatically retries on failure, falls back to cheaper models
response = robust_chat([{"role": "user", "content": "Hello"}])
```

---

## CLI Reference

Rich/Typer command-line interface.

### Installation

```bash
pip install typer[all]
```

### Commands

#### `chat`

Send a chat message.

```bash
python -m cli.stratifyai_cli chat [OPTIONS] [TEXT]

Options:
  -p, --provider TEXT      Provider name
  -m, --model TEXT         Model name
  -t, --temperature FLOAT  Temperature (0.0-2.0)
  -s, --stream            Enable streaming
  --file PATH             Load content from file
  --cache-control         Enable prompt caching
```

**Examples:**
```bash
# Simple chat
python -m cli.stratifyai_cli chat "Hello" -p openai -m gpt-4o-mini

# Streaming
python -m cli.stratifyai_cli chat "Write a poem" -p anthropic -m claude-sonnet-4-5-20250929 -s

# From file
python -m cli.stratifyai_cli chat --file document.txt -p openai -m gpt-4o-mini

# With prompt caching
python -m cli.stratifyai_cli chat "Summarize" --file large_doc.txt --cache-control
```

#### `interactive`

Interactive chat mode with conversation history.

```bash
python -m cli.stratifyai_cli interactive [OPTIONS]

Options:
  -p, --provider TEXT  Provider name
  -m, --model TEXT     Model name
```

**Example:**
```bash
python -m cli.stratifyai_cli interactive -p anthropic -m claude-sonnet-4-5-20250929
```

#### `models`

List available models.

```bash
python -m cli.stratifyai_cli models [OPTIONS]

Options:
  -p, --provider TEXT  Filter by provider
```

**Example:**
```bash
# All models
python -m cli.stratifyai_cli models

# OpenAI models only
python -m cli.stratifyai_cli models -p openai
```

#### `providers`

List all providers.

```bash
python -m cli.stratifyai_cli providers
```

#### `route`

Auto-select best model via router.

```bash
python -m cli.stratifyai_cli route [OPTIONS] TEXT

Options:
  --strategy [cost|quality|latency|hybrid]  Routing strategy
```

**Example:**
```bash
# Cost-optimized
python -m cli.stratifyai_cli route "What is 2+2?" --strategy cost

# Quality-optimized for complex task
python -m cli.stratifyai_cli route "Prove Fermat's Last Theorem" --strategy quality
```

#### `cache-stats`

Display cache statistics.

```bash
python -m cli.stratifyai_cli cache-stats
```

### Environment Variables

```bash
# Set default provider and model
export STRATUMAI_PROVIDER=anthropic
export STRATUMAI_MODEL=claude-sonnet-4-5-20250929

# Now you can omit --provider and --model
python -m cli.stratifyai_cli chat "Hello"
```

See [cli-usage.md](cli-usage.md) for complete CLI documentation.

---

## Advanced Usage

### Multi-Provider Fallback

```python
from stratifyai import LLMClient
from stratifyai.retry import with_retry, RetryConfig

client = LLMClient()

config = RetryConfig(
    max_retries=3,
    fallback_models=["gpt-4.1", "claude-sonnet-4-5-20250929", "gpt-4o-mini"]
)

@with_retry(config)
def resilient_chat(messages):
    return client.chat(model="gpt-4.1", messages=messages)

# Tries gpt-4.1, falls back to claude, then gpt-4o-mini
response = resilient_chat([{"role": "user", "content": "Hello"}])
print(f"Model used: {response.model}")
```

### Budget-Aware Routing

```python
from stratifyai import Router, CostTracker
from stratifyai.router import RoutingStrategy, RoutingConstraints

tracker = CostTracker(budget_limit=5.0)
router = Router(client)

# Route with cost constraint
response = router.route(
    messages=[{"role": "user", "content": "Complex task"}],
    strategy=RoutingStrategy.QUALITY,
    constraints=RoutingConstraints(
        max_cost_per_1k_tokens=0.005  # Max $0.005 per 1K tokens
    )
)

tracker.record_call(response.model, response.provider, response.usage)

within_budget, remaining = tracker.check_budget()
print(f"Budget remaining: ${remaining:.2f}")
```

### Streaming with Cost Tracking

```python
from stratifyai import LLMClient, CostTracker

client = LLMClient()
tracker = CostTracker()

full_content = ""
for chunk in client.chat_stream(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Write a story"}]
):
    print(chunk.content, end="", flush=True)
    full_content += chunk.content

# Final chunk contains complete usage
final_chunk = chunk
tracker.record_call(final_chunk.model, final_chunk.provider, final_chunk.usage)
```

---

## Performance Tips

1. **Use streaming for long responses** to improve perceived latency
2. **Enable response caching** for repeated queries (100% cost reduction)
3. **Use prompt caching** for long contexts (up to 90% cost reduction)
4. **Use Router with COST strategy** for simple queries to minimize spend
5. **Batch requests** when possible instead of sequential calls
6. **Use local models (Ollama)** for development and testing
7. **Set budget limits** with CostTracker to prevent overruns

---

## Best Practices

1. **Always handle exceptions** - Network failures, rate limits, and API errors can occur
2. **Use type hints** - Full type safety throughout the library
3. **Monitor costs** - Use CostTracker for all production deployments
4. **Test with cheap models first** - Use gpt-4o-mini or claude-haiku-4 during development
5. **Use environment variables** - Never hardcode API keys
6. **Enable logging** - Use logging decorator for debugging
7. **Set reasonable timeouts** - Avoid hanging on slow API responses
8. **Cache aggressively** - Response caching can save 90%+ on costs

---

## Troubleshooting

### Common Issues

**Problem:** `ProviderNotFoundError`  
**Solution:** Ensure API key is set in environment variables

**Problem:** `RateLimitException`  
**Solution:** Enable retry logic with fallback models

**Problem:** High costs  
**Solution:** Use Router with COST strategy, enable caching

**Problem:** Slow responses  
**Solution:** Use streaming, or Router with LATENCY strategy

**Problem:** `ModelNotFoundError`  
**Solution:** Check model name spelling, use `client.list_models(provider)`

---

## API Version Compatibility

| StratifyAI Version | OpenAI SDK | Anthropic SDK | Google SDK |
|-------------------|------------|---------------|------------|
| 1.0.0 | >=1.12.0 | >=0.18.0 | >=0.3.0 |

---

## Support

For issues, questions, or feature requests, please contact the project maintainer.

**Documentation:** See [README.md](../README.md), [AGENTS.md](../AGENTS.md)  
**Examples:** See [examples/](../examples/)  
**Tests:** Run `pytest` in project root
