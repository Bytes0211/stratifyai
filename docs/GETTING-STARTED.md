# Getting Started with StratifyAI

A step-by-step guide to using StratifyAI, the unified multi-provider LLM abstraction module.

**Last Updated:** February 6, 2026

---

## What is StratifyAI?

StratifyAI lets you use any LLM provider (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, AWS Bedrock) through a single, consistent API. Switch models without changing your code, track costs automatically, and leverage intelligent routing to select the best model for each task.

**Key Benefits:**
- 🔄 **No Vendor Lock-In**: Switch between 9 providers seamlessly
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
git clone https://github.com/Bytes0211/stratifyai.git
cd stratifyai

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure API Keys

**Requirements:** At least ONE provider API key is required to use StratifyAI. You only need keys for the providers you plan to use.

#### Step 1: Copy the Example Environment File

StratifyAI includes a template `.env.example` file with all supported providers:

```bash
# Copy the example file to create your .env
cp .env.example .env
```

#### Step 2: Get API Keys from Providers

Choose one or more providers and obtain API keys:

##### Primary Providers (Most Popular)

**OpenAI** (GPT-4, GPT-4o, o1, o3-mini)
- **Get your key:** https://platform.openai.com/api-keys
- **Steps:**
  1. Sign up or log in to OpenAI Platform
  2. Navigate to API Keys section
  3. Click "Create new secret key"
  4. Copy the key (starts with `sk-proj-` or `sk-`)
- **Add to .env:** `OPENAI_API_KEY=sk-proj-your-key-here`

**Anthropic** (Claude 3.5, Claude 4, Claude 4.5)
- **Get your key:** https://console.anthropic.com/settings/keys
- **Steps:**
  1. Sign up or log in to Anthropic Console
  2. Go to Settings → API Keys
  3. Click "Create Key"
  4. Copy the key (starts with `sk-ant-`)
- **Add to .env:** `ANTHROPIC_API_KEY=sk-ant-your-key-here`

**Google Gemini** (Gemini 1.5, Gemini 2.0, Gemini 2.5)
- **Get your key:** https://makersuite.google.com/app/apikey
- **Steps:**
  1. Sign in with Google account
  2. Click "Get API Key" or "Create API Key"
  3. Copy the key (starts with `AIza`)
- **Add to .env:** `GOOGLE_API_KEY=AIzaYour-Key-Here`

##### AWS Bedrock (Claude, Llama, Mistral, Nova via AWS)

**Option 1: Bearer Token** (Simplest)
- **Get credentials:** https://docs.aws.amazon.com/bedrock/
- **Add to .env:** `AWS_BEARER_TOKEN_BEDROCK=your-bearer-token`

**Option 2: Access Key + Secret Key**
```bash
# Add both to .env
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_DEFAULT_REGION=us-east-1  # Optional, defaults to us-east-1
```

**Option 3: IAM Roles** (When running on AWS infrastructure)
- No explicit credentials needed
- boto3 automatically uses the instance's IAM role

**Option 4: AWS Credentials File**
```bash
# Configure AWS CLI (creates ~/.aws/credentials)
aws configure
```

##### Alternative Providers (Optional)

**DeepSeek** (deepseek-chat, deepseek-reasoner, deepseek-r1)
- **Get your key:** https://platform.deepseek.com/api-docs/
- **Add to .env:** `DEEPSEEK_API_KEY=sk-your-key-here`

**Groq** (Fast inference for Llama, Mixtral, Gemma)
- **Get your key:** https://console.groq.com/keys
- **Add to .env:** `GROQ_API_KEY=gsk_your-key-here`

**Grok (X.AI)** (grok-beta)
- **Get your key:** https://x.ai/api
- **Steps:**
  1. Visit X.AI API console
  2. Sign up or log in with X/Twitter account
  3. Generate API key
  4. Copy the key (starts with `xai-`)
- **Add to .env:** `GROK_API_KEY=xai-your-key-here`

**OpenRouter** (Access 100+ models through one API)
- **Get your key:** https://openrouter.ai/keys
- **Add to .env:** `OPENROUTER_API_KEY=sk-or-v1-your-key-here`

**Ollama** (Local models - no API key needed)
- **Install:** https://ollama.ai/download
- **Note:** Runs locally on localhost:11434, no API key required
- **Optional .env:** `OLLAMA_BASE_URL=http://localhost:11434`

#### Step 3: Add Keys to Your .env File

Open the `.env` file and add your API keys:

```bash
# Example .env file (use your actual keys)

# Primary Providers
OPENAI_API_KEY=sk-proj-8B5oLousaY9Er2xwxrAOxFtr8hkwhWF8NsUrCEz...
ANTHROPIC_API_KEY=sk-ant-api03-6WeN6pEHU-3XFbfNwcUtWR2xjj4Vo7b...
GOOGLE_API_KEY=AIzaSyBZqW4tMlZiBbFkr9FXMwnB6vce00p3Z1k

# AWS Bedrock (choose one authentication method)
AWS_BEARER_TOKEN_BEDROCK=ABSKQmVkcm9ja0FQSUtleS1hZm0w...
# OR
# AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
# AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
# AWS_DEFAULT_REGION=us-east-1

# Alternative Providers (optional)
DEEPSEEK_API_KEY=sk-c4b3123546b1480d904f7d4d2f7cb892
GROQ_API_KEY=gsk_h8NUJy5XIMtVIjd2fzBbWGdyb3FY0YUHeAyNqb...
GROK_API_KEY=xai-IySZoehC5IP2Zspnj6b7L64KoB5Z8qn1UQZgPo...
OPENROUTER_API_KEY=sk-or-v1-eede4b25662eaf2e25d5fa1590...

# Ollama (local models - no key needed)
# OLLAMA_BASE_URL=http://localhost:11434
```

#### Step 4: Verify Your Configuration

Use the built-in CLI command to check which providers are configured:

```bash
# Activate virtual environment first
source .venv/bin/activate

# Check API key status
stratifyai check-keys
```

**Expected Output:**
```
🔑 StratifyAI API Key Status
════════════════════════════════════════════════════════

Provider              Status          Environment Variable
────────────────────────────────────────────────────────
OpenAI                ✓ Configured    OPENAI_API_KEY
Anthropic             ✓ Configured    ANTHROPIC_API_KEY
Google Gemini         ✓ Configured    GOOGLE_API_KEY
DeepSeek              ✓ Configured    DEEPSEEK_API_KEY
Groq                  ✓ Configured    GROQ_API_KEY
Grok (X.AI)           ✓ Configured    GROK_API_KEY
OpenRouter            ⚠ Missing       OPENROUTER_API_KEY
Ollama                ✓ Configured    OLLAMA_API_KEY
AWS Bedrock           ✓ Configured    AWS_BEARER_TOKEN_BEDROCK

6/9 providers configured
```

#### Step 5: Test Your Setup

Verify that StratifyAI can connect to your configured providers:

```bash
# Test with OpenAI
stratifyai chat -p openai -m gpt-4o-mini -t "Hello, StratifyAI!"

# Test with Anthropic
stratifyai chat -p anthropic -m claude-sonnet-4-5 -t "Hello, Claude!"

# Test with Google
stratifyai chat -p google -m gemini-2.5-flash-lite -t "Hello, Gemini!"
```

**Expected Output:**
```
✓ Response from gpt-4o-mini

Hello! I'm StratifyAI, ready to help you with any questions or tasks.

📊 Response Metadata:
  • Provider: openai
  • Model: gpt-4o-mini
  • Tokens: 23 (input: 12, output: 11)
  • Cost: $0.000003
  • Latency: 847ms
```

#### Security Best Practices

**⚠️ CRITICAL: Never commit API keys to version control!**

1. **Verify .gitignore includes .env:**
   ```bash
   # Check that .env is ignored
   git check-ignore .env
   # Should output: .env
   ```

2. **Use separate keys for different environments:**
   - Development: `.env.development`
   - Staging: `.env.staging`
   - Production: Use secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)

3. **Rotate keys regularly:**
   - Rotate API keys every 90 days
   - Immediately rotate if compromised

4. **Set budget limits:**
   - OpenAI: https://platform.openai.com/account/billing/limits
   - Anthropic: https://console.anthropic.com/settings/limits
   - Most providers offer usage limits and alerts

5. **Monitor usage:**
   ```bash
   # Use StratifyAI's cost tracking
   stratifyai cache-stats
   ```

6. **Use environment-specific keys:**
   ```bash
   # Development
   export OPENAI_API_KEY=$OPENAI_DEV_KEY
   
   # Production
   export OPENAI_API_KEY=$OPENAI_PROD_KEY
   ```

#### Troubleshooting API Keys

**Problem: "Missing API key for [provider]"**

Solution:
```bash
# 1. Check if .env file exists
ls -la .env

# 2. Verify the key is in .env
grep OPENAI_API_KEY .env

# 3. Check if environment variable is loaded
echo $OPENAI_API_KEY

# 4. Manually export the key (temporary)
export OPENAI_API_KEY="your-key-here"

# 5. Pass key directly in code
client = LLMClient(provider="openai", api_key="your-key-here")
```

**Problem: "Authentication failed"**

Solution:
- Verify the API key is correct (no extra spaces, complete key)
- Check if the key has been revoked or expired
- Ensure you have credits/quota remaining
- Verify the key format matches the provider:
  - OpenAI: `sk-proj-` or `sk-`
  - Anthropic: `sk-ant-`
  - Google: `AIza`
  - Grok: `xai-`

**Problem: "Provider not available"**

Solution:
```python
# Check which providers are available
from stratifyai.api_key_helper import APIKeyHelper
available = APIKeyHelper.check_available_providers()
print(available)
# Output: {'openai': True, 'anthropic': True, 'google': False, ...}
```

**Problem: AWS Bedrock authentication issues**

Solution:
```bash
# Option 1: Check bearer token
echo $AWS_BEARER_TOKEN_BEDROCK

# Option 2: Check AWS credentials
aws configure list

# Option 3: Test AWS connection
aws bedrock list-foundation-models --region us-east-1

# Option 4: Verify IAM permissions
# Ensure your IAM user/role has bedrock:InvokeModel permission
```

---

## Quick Start

### Your First Request (Python)

**Note:** StratifyAI is async-first. Use `await` for async code or `_sync` methods for convenience.

```python
from stratifyai import LLMClient
from stratifyai.models import Message

# Initialize client (reads API keys from environment)
client = LLMClient()

# Option 1: Sync wrapper (simpler for scripts)
response = client.chat_sync(
    model="gpt-4o-mini",
    messages=[Message(role="user", content="Explain AI in one sentence")]
)

print(response.content)
print(f"Cost: ${response.usage.cost_usd:.4f}")

# Option 2: Async (recommended for production)
# import asyncio
# async def main():
#     response = await client.chat(
#         model="gpt-4o-mini",
#         messages=[Message(role="user", content="Explain AI in one sentence")]
#     )
#     print(response.content)
# asyncio.run(main())
```

**Output:**
```
Artificial intelligence is the simulation of human intelligence by computer systems.
Cost: $0.0002
```

### Your First Request (CLI)

```bash
# Simple chat command
python -m cli.stratifyai_cli chat "Explain AI in one sentence" \
  --provider openai \
  --model gpt-4o-mini

# Or use environment variables
export STRATUMAI_PROVIDER=openai
export STRATUMAI_MODEL=gpt-4o-mini
python -m cli.stratifyai_cli chat "Explain AI in one sentence"
```

---

## Basic Usage

### Sending Messages

```python
from stratifyai import LLMClient

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

The power of StratifyAI: Switch providers without changing your code!

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
python -m cli.stratifyai_cli chat "Write a poem" \
  --provider openai \
  --model gpt-4o-mini \
  --stream
```

---

## Cost Tracking

Monitor and control your LLM spending.

### Basic Cost Tracking

```python
from stratifyai import LLMClient, CostTracker

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
DEV_MODEL = "gpt-4o-mini"  # $0.15 per 1M input, $0.60 per 1M output
PROD_MODEL = "gpt-4o"      # $2.50 per 1M input, $10.0 per 1M output

# Development
response = client.chat_sync(model=DEV_MODEL, messages=[...])

# Production (after testing)
# response = client.chat_sync(model=PROD_MODEL, messages=[...])
```

---

## Intelligent Routing

Let StratifyAI select the best model for your task.

### Basic Routing

```python
from stratifyai import Router, RoutingStrategy

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
python -m cli.stratifyai_cli route "What is machine learning?" --strategy hybrid

# Cost-optimized
python -m cli.stratifyai_cli route "Simple question" --strategy cost

# Quality-optimized
python -m cli.stratifyai_cli route "Complex analysis task" --strategy quality
```

---

## Caching

Save costs and latency with response and prompt caching.

### Response Caching

Cache identical requests to avoid duplicate API calls.

```python
from stratifyai.caching import cache_response

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
from stratifyai.models import Message

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

StratifyAI includes a powerful CLI for terminal usage.

### Interactive Mode

```bash
# Start interactive chat
python -m cli.stratifyai_cli interactive \
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
python -m cli.stratifyai_cli chat "Hello" -p openai -m gpt-4o-mini

# Streaming
python -m cli.stratifyai_cli chat "Write a poem" -p openai -m gpt-4o-mini --stream

# List all models
python -m cli.stratifyai_cli models

# List models for specific provider
python -m cli.stratifyai_cli models --provider anthropic

# List all providers
python -m cli.stratifyai_cli providers

# Auto-route to best model
python -m cli.stratifyai_cli route "Complex question" --strategy quality
```

### Environment Variables

```bash
# Set defaults
export STRATUMAI_PROVIDER=anthropic
export STRATUMAI_MODEL=claude-sonnet-4-5-20250929

# Now you can omit --provider and --model
python -m cli.stratifyai_cli chat "Hello"
```

### Load Content from Files

```bash
# Chat about a file
python -m cli.stratifyai_cli chat --file document.txt \
  -p openai -m gpt-4o-mini

# With custom prompt
python -m cli.stratifyai_cli chat "Summarize this:" --file document.txt \
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
   from stratifyai.retry import with_retry, RetryConfig
   
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
   from stratifyai.utils import log_llm_call
   
   @log_llm_call
   def my_function():
       return client.chat(...)
   ```

### Build Your First App

**Idea:** Build a code review assistant

```python
from stratifyai import LLMClient, Router, RoutingStrategy

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
from stratifyai.exceptions import (
    RateLimitError,
    InvalidModelError,
    ProviderAPIError
)

try:
    response = client.chat_sync(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}]
    )
except InvalidModelError:
    print("Model not found - check spelling")
except RateLimitError as e:
    print(f"Rate limited - retry after {e.retry_after}s")
except ProviderAPIError as e:
    print(f"API error: {e}")
```

---

## Tips and Best Practices

1. **Start with cheap models during development**
   - Use `gpt-4o-mini` ($0.15/1M input, $0.60/1M output) instead of `gpt-4o` ($2.50/1M input, $10.0/1M output)

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
cd stratifyai

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
model = "gpt-4o-mini"  # instead of "gpt-4o"

# 2. Enable caching
from stratifyai.caching import cache_response

@cache_response(ttl=3600)
def ask(question):
    return client.chat(model="gpt-4o-mini", messages=[...])

# 3. Use Router with COST strategy
from stratifyai import Router, RoutingStrategy

router = Router(client)
response = router.route(messages=[...], strategy=RoutingStrategy.COST)
```

---

## What You've Learned

✅ How to install and configure StratifyAI  
✅ How to send basic chat requests  
✅ How to switch between providers seamlessly  
✅ How to use streaming for better UX  
✅ How to track and control costs  
✅ How to use intelligent routing  
✅ How to leverage caching for cost savings  
✅ How to use the CLI interface  

**Next:** Check out [API-REFERENCE.md](API-REFERENCE.md) for complete API documentation, or explore [examples/](../examples/) for real-world patterns.

Happy building! 🚀
