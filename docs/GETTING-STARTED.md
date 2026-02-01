# Getting Started with StratumAI

A step-by-step guide to using StratumAI, the unified multi-provider LLM abstraction module.

**Last Updated:** February 1, 2026

---

## What is StratumAI?

StratumAI lets you use any LLM provider (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama) through a single, consistent API. Switch models without changing your code, track costs automatically, and leverage intelligent routing to select the best model for each task.

**Key Benefits:**
- 🔄 **No Vendor Lock-In**: Switch between 8+ providers seamlessly
- 💰 **Cost Tracking**: Automatic token usage and cost calculation
- 🧠 **Smart Routing**: Select optimal models based on complexity
- ⚡ **Production Ready**: Retry logic, caching, error handling
- 🎯 **Type Safe**: Full type hints throughout

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Basic Usage](#basic-usage)
4. [Switching Providers](#switching-providers)
5. [Streaming Responses](#streaming-responses)
6. [Cost Tracking](#cost-tracking)
7. [Intelligent Routing](#intelligent-routing)
8. [Caching](#caching)
9. [CLI Usage](#cli-usage)
10. [Next Steps](#next-steps)

---

## Installation

### Prerequisites

- Python 3.10 or higher
- API keys for providers you want to use

### Clone and Setup

```bash
# Clone the repository
git clone <repo-url>
cd stratumai

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure API Keys

Create a `.env` file in the project root:

```bash
# Required: At least one provider key
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional: Additional providers
DEEPSEEK_API_KEY=...
GROQ_API_KEY=...
XAI_API_KEY=...
OPENROUTER_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434
```

**Security Note:** Never commit `.env` files to version control!

---

## Quick Start

### Your First Request (Python)

```python
from llm_abstraction import LLMClient

# Initialize client (reads API keys from environment)
client = LLMClient()

# Send a message to GPT-4o-mini
response = client.chat(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Explain AI in one sentence"}]
)

print(response.content)
print(f"Cost: ${response.usage.cost_usd:.4f}")
```

**Output:**
```
Artificial intelligence is the simulation of human intelligence by computer systems.
Cost: $0.0002
```

### Your First Request (CLI)

```bash
# Simple chat command
python -m cli.stratumai_cli chat "Explain AI in one sentence" \
  --provider openai \
  --model gpt-4o-mini

# Or use environment variables
export STRATUMAI_PROVIDER=openai
export STRATUMAI_MODEL=gpt-4o-mini
python -m cli.stratumai_cli chat "Explain AI in one sentence"
```

---

## Basic Usage

### Sending Messages

```python
from llm_abstraction import LLMClient

client = LLMClient()

# Simple user message
response = client.chat(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "What is the capital of France?"}
    ]
)
print(response.content)  # "The capital of France is Paris."
```

### System Messages

```python
# Add system message for context
response = client.chat(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful math tutor."},
        {"role": "user", "content": "What is 15 * 24?"}
    ]
)
```

### Temperature and Parameters

```python
# Adjust creativity with temperature
response = client.chat(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Write a creative story"}],
    temperature=0.9,  # Higher = more creative (0.0-2.0)
    max_tokens=500    # Limit response length
)
```

**Temperature Guide:**
- `0.0-0.3`: Deterministic, factual (good for coding, analysis)
- `0.4-0.7`: Balanced (default)
- `0.8-1.5`: Creative (good for writing, brainstorming)

---

## Switching Providers

The power of StratumAI: Switch providers without changing your code!

### Switch to Anthropic (Claude)

```python
# Same interface, different provider
response = client.chat(
    model="claude-sonnet-4-5-20250929",  # Just change the model name!
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Switch to Google (Gemini)

```python
response = client.chat(
    model="gemini-2.5-flash-lite",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Switch to Local Models (Ollama)

```python
# No API costs - runs locally!
response = client.chat(
    model="llama3.3",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Compare Providers

```python
models = [
    "gpt-4o-mini",                    # OpenAI
    "claude-haiku-4",                 # Anthropic
    "gemini-2.5-flash-lite",          # Google
    "deepseek-chat",                  # DeepSeek
    "llama-3.3-70b-versatile",        # Groq
]

question = "What is machine learning?"

for model in models:
    response = client.chat(
        model=model,
        messages=[{"role": "user", "content": question}]
    )
    print(f"\n{model}:")
    print(f"  Answer: {response.content[:100]}...")
    print(f"  Cost: ${response.usage.cost_usd:.6f}")
```

---

## Streaming Responses

Stream responses token-by-token for better UX.

### Basic Streaming

```python
# Stream the response in real-time
for chunk in client.chat_stream(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Write a short poem"}]
):
    print(chunk.content, end="", flush=True)
```

**Output** (streamed in real-time):
```
Roses are red,
Violets are blue,
AI is helpful,
And poetry too!
```

### Streaming with Full Response

```python
# Collect full response while streaming
full_content = ""
usage_info = None

for chunk in client.chat_stream(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Count to 10"}]
):
    print(chunk.content, end="", flush=True)
    full_content += chunk.content
    usage_info = chunk.usage  # Final chunk has complete usage

print(f"\n\nTotal tokens: {usage_info.total_tokens}")
print(f"Cost: ${usage_info.cost_usd:.4f}")
```

### CLI Streaming

```bash
python -m cli.stratumai_cli chat "Write a poem" \
  --provider openai \
  --model gpt-4o-mini \
  --stream
```

---

## Cost Tracking

Monitor and control your LLM spending.

### Basic Cost Tracking

```python
from llm_abstraction import LLMClient, CostTracker

client = LLMClient()
tracker = CostTracker(budget_limit=5.0)  # $5 budget

# Make some requests
for i in range(10):
    response = client.chat(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"Question {i}"}]
    )
    
    # Record the cost
    tracker.record_call(
        model=response.model,
        provider=response.provider,
        usage=response.usage
    )
    
    # Check budget
    within_budget, remaining = tracker.check_budget()
    if not within_budget:
        print(f"Budget exceeded!")
        break

# Get summary
summary = tracker.get_summary()
print(f"\nTotal cost: ${summary['total_cost']:.4f}")
print(f"Total calls: {summary['total_calls']}")
print(f"By provider: {summary['by_provider']}")
```

### Cost-Aware Development

```python
# Test with cheap models first
DEV_MODEL = "gpt-4o-mini"  # $0.00015 per 1K tokens
PROD_MODEL = "gpt-4.1"     # $0.0050 per 1K tokens

# Development
response = client.chat(model=DEV_MODEL, messages=[...])

# Production (after testing)
# response = client.chat(model=PROD_MODEL, messages=[...])
```

---

## Intelligent Routing

Let StratumAI select the best model for your task.

### Basic Routing

```python
from llm_abstraction import Router, RoutingStrategy

# Initialize router
router = Router(client, default_strategy=RoutingStrategy.HYBRID)

# Simple question - router selects cheap, fast model
response = router.route(
    messages=[{"role": "user", "content": "What is 2+2?"}],
    strategy=RoutingStrategy.COST
)
print(f"Selected: {response.model}")  # Likely: gpt-4o-mini or groq model

# Complex question - router selects powerful model
response = router.route(
    messages=[{"role": "user", "content": "Prove Fermat's Last Theorem"}],
    strategy=RoutingStrategy.QUALITY
)
print(f"Selected: {response.model}")  # Likely: gpt-4.1 or claude-sonnet-4
```

### Routing Strategies

```python
# 1. COST - Minimize cost (good for simple queries)
response = router.route(
    messages=[{"role": "user", "content": "What's the weather?"}],
    strategy=RoutingStrategy.COST
)

# 2. QUALITY - Maximize quality (good for complex reasoning)
response = router.route(
    messages=[{"role": "user", "content": "Analyze this complex data..."}],
    strategy=RoutingStrategy.QUALITY
)

# 3. LATENCY - Minimize latency (good for real-time apps)
response = router.route(
    messages=[{"role": "user", "content": "Quick answer please"}],
    strategy=RoutingStrategy.LATENCY
)

# 4. HYBRID - Balance based on complexity (default)
response = router.route(
    messages=[{"role": "user", "content": "Any question"}],
    strategy=RoutingStrategy.HYBRID
)
```

### Complexity Analysis

```python
# Analyze how complex your prompt is (0.0-1.0)
complexity = router.analyze_complexity([
    {"role": "user", "content": "What is 2+2?"}
])
print(f"Complexity: {complexity:.2f}")  # ~0.15 (simple)

complexity = router.analyze_complexity([
    {"role": "user", "content": "Prove that the square root of 2 is irrational"}
])
print(f"Complexity: {complexity:.2f}")  # ~0.75 (complex)
```

### CLI Routing

```bash
# Auto-select best model
python -m cli.stratumai_cli route "What is machine learning?" --strategy hybrid

# Cost-optimized
python -m cli.stratumai_cli route "Simple question" --strategy cost

# Quality-optimized
python -m cli.stratumai_cli route "Complex analysis task" --strategy quality
```

---

## Caching

Save costs and latency with response and prompt caching.

### Response Caching

Cache identical requests to avoid duplicate API calls.

```python
from llm_abstraction.caching import cache_response

# Decorator automatically caches responses
@cache_response(ttl=3600)  # Cache for 1 hour
def ask_llm(question: str) -> str:
    response = client.chat(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}]
    )
    return response.content

# First call - hits API ($0.0002)
answer1 = ask_llm("What is AI?")  # ~2 seconds

# Second call - cached ($0.0000)
answer2 = ask_llm("What is AI?")  # <1ms, same answer

print(f"Same answer: {answer1 == answer2}")  # True
```

**Cost Savings:** 100% for cached requests

### Prompt Caching

Cache long context that you reuse (Anthropic, OpenAI, Google).

```python
from llm_abstraction.models import Message

# Load a long document once
long_document = open("large_file.txt").read()  # 50,000 tokens

# First request - creates cache (~$0.05)
messages = [
    Message(
        role="user",
        content=long_document,
        cache_control={"type": "ephemeral"}  # Cache this content
    ),
    Message(role="user", content="Summarize this document")
]

response1 = client.chat(
    model="claude-sonnet-4-5-20250929",
    messages=messages
)
print(f"Cost: ${response1.usage.cost_usd:.4f}")  # ~$0.05
print(f"Cache writes: {response1.usage.cache_creation_tokens}")  # 50,000

# Second request - reads from cache (~$0.005, 90% savings!)
messages = [
    Message(
        role="user",
        content=long_document,  # Same content - cached!
        cache_control={"type": "ephemeral"}
    ),
    Message(role="user", content="What are the key themes?")
]

response2 = client.chat(
    model="claude-sonnet-4-5-20250929",
    messages=messages
)
print(f"Cost: ${response2.usage.cost_usd:.4f}")  # ~$0.005
print(f"Cache reads: {response2.usage.cache_read_tokens}")  # 50,000
```

**Cost Savings:** Up to 90% for cached prompts

See [CACHING.md](CACHING.md) for complete caching documentation.

---

## CLI Usage

StratumAI includes a powerful CLI for terminal usage.

### Interactive Mode

```bash
# Start interactive chat
python -m cli.stratumai_cli interactive \
  --provider anthropic \
  --model claude-sonnet-4-5-20250929

# Now chat back and forth:
You: What is machine learning?
Assistant: Machine learning is...

You: Give me an example
Assistant: For example...

You: exit  # Exit the conversation
```

### Quick Commands

```bash
# Single message
python -m cli.stratumai_cli chat "Hello" -p openai -m gpt-4o-mini

# Streaming
python -m cli.stratumai_cli chat "Write a poem" -p openai -m gpt-4o-mini --stream

# List all models
python -m cli.stratumai_cli models

# List models for specific provider
python -m cli.stratumai_cli models --provider anthropic

# List all providers
python -m cli.stratumai_cli providers

# Auto-route to best model
python -m cli.stratumai_cli route "Complex question" --strategy quality
```

### Environment Variables

```bash
# Set defaults
export STRATUMAI_PROVIDER=anthropic
export STRATUMAI_MODEL=claude-sonnet-4-5-20250929

# Now you can omit --provider and --model
python -m cli.stratumai_cli chat "Hello"
```

### Load Content from Files

```bash
# Chat about a file
python -m cli.stratumai_cli chat --file document.txt \
  -p openai -m gpt-4o-mini

# With custom prompt
python -m cli.stratumai_cli chat "Summarize this:" --file document.txt \
  -p openai -m gpt-4o-mini
```

See [cli-usage.md](cli-usage.md) for complete CLI documentation.

---

## Next Steps

### Learn More

1. **Read API Reference**: See [API-REFERENCE.md](API-REFERENCE.md) for complete API documentation
2. **Explore Examples**: Check [examples/](../examples/) for real-world usage patterns
3. **Study Caching**: Read [CACHING.md](CACHING.md) to optimize costs
4. **Review Tests**: Look at `tests/` to understand edge cases

### Try Advanced Features

1. **Retry Logic**: Automatic fallback to alternative models
   ```python
   from llm_abstraction.retry import with_retry, RetryConfig
   
   @with_retry(RetryConfig(fallback_models=["gpt-4.1", "gpt-4o-mini"]))
   def robust_chat(messages):
       return client.chat(model="gpt-4.1", messages=messages)
   ```

2. **Budget Management**: Set spending limits
   ```python
   tracker = CostTracker(budget_limit=10.0, alert_threshold=0.8)
   ```

3. **Logging**: Track all LLM calls
   ```python
   from llm_abstraction.utils import log_llm_call
   
   @log_llm_call
   def my_function():
       return client.chat(...)
   ```

### Build Your First App

**Idea:** Build a code review assistant

```python
from llm_abstraction import LLMClient, Router, RoutingStrategy

client = LLMClient()
router = Router(client)

def review_code(code: str) -> str:
    """Review code using intelligent routing."""
    response = router.route(
        messages=[
            {"role": "system", "content": "You are a code review expert."},
            {"role": "user", "content": f"Review this code:\n\n{code}"}
        ],
        strategy=RoutingStrategy.QUALITY  # Use best model for code review
    )
    return response.content

# Test it
code = """
def add(a, b):
    return a + b
"""

review = review_code(code)
print(review)
```

### Get Help

- **Documentation**: See docs folder for guides
- **Examples**: Check examples folder for patterns
- **Tests**: Run `pytest` to see comprehensive test suite
- **Issues**: Contact project maintainer for support

---

## Common Patterns

### Pattern 1: Multi-Turn Conversation

```python
conversation = [
    {"role": "system", "content": "You are a helpful assistant."}
]

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break
    
    conversation.append({"role": "user", "content": user_input})
    
    response = client.chat(model="gpt-4o-mini", messages=conversation)
    
    print(f"Assistant: {response.content}")
    conversation.append({"role": "assistant", "content": response.content})
```

### Pattern 2: Batch Processing

```python
questions = [
    "What is Python?",
    "What is JavaScript?",
    "What is Go?"
]

results = []
for question in questions:
    response = client.chat(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}]
    )
    results.append(response.content)
```

### Pattern 3: Error Handling

```python
from llm_abstraction.exceptions import (
    RateLimitException,
    ModelNotFoundError,
    ProviderAPIError
)

try:
    response = client.chat(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}]
    )
except ModelNotFoundError:
    print("Model not found - check spelling")
except RateLimitException as e:
    print(f"Rate limited - retry after {e.retry_after}s")
except ProviderAPIError as e:
    print(f"API error: {e}")
```

---

## Tips and Best Practices

1. **Start with cheap models during development**
   - Use `gpt-4o-mini` ($0.00015/1K tokens) instead of `gpt-4.1` ($0.0050/1K tokens)

2. **Use streaming for long responses**
   - Improves user experience with instant feedback

3. **Enable caching for repeated queries**
   - Response caching: 100% cost savings
   - Prompt caching: up to 90% savings

4. **Monitor costs with CostTracker**
   - Set budget limits to avoid surprises

5. **Use Router for intelligent model selection**
   - COST for simple queries
   - QUALITY for complex reasoning
   - HYBRID for balanced approach

6. **Test locally with Ollama**
   - No API costs, instant responses

7. **Handle errors gracefully**
   - Use try/except for rate limits and API errors

8. **Never hardcode API keys**
   - Use environment variables or `.env` file

---

## Troubleshooting

### Problem: ModuleNotFoundError

**Solution:**
```bash
# Make sure you're in the right directory
cd stratumai

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Problem: API key not found

**Solution:**
```bash
# Check .env file exists
cat .env

# Make sure key is set
echo $OPENAI_API_KEY

# Or set it manually
export OPENAI_API_KEY=sk-...
```

### Problem: Model not found

**Solution:**
```python
# List available models for provider
models = client.list_models("openai")
print(models)

# Use exact model name from list
response = client.chat(model=models[0], messages=[...])
```

### Problem: High costs

**Solution:**
```python
# 1. Use cheaper models
model = "gpt-4o-mini"  # instead of "gpt-4.1"

# 2. Enable caching
from llm_abstraction.caching import cache_response

@cache_response(ttl=3600)
def ask(question):
    return client.chat(model="gpt-4o-mini", messages=[...])

# 3. Use Router with COST strategy
from llm_abstraction import Router, RoutingStrategy

router = Router(client)
response = router.route(messages=[...], strategy=RoutingStrategy.COST)
```

---

## What You've Learned

✅ How to install and configure StratumAI  
✅ How to send basic chat requests  
✅ How to switch between providers seamlessly  
✅ How to use streaming for better UX  
✅ How to track and control costs  
✅ How to use intelligent routing  
✅ How to leverage caching for cost savings  
✅ How to use the CLI interface  

**Next:** Check out [API-REFERENCE.md](API-REFERENCE.md) for complete API documentation, or explore [examples/](../examples/) for real-world patterns.

Happy building! 🚀
