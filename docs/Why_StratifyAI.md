# Why StratifyAI?

## The Problem

Every major AI provider has its own API, pricing model, rate limits, and capabilities. Building an application that uses AI today means picking one provider and coupling your code to it — or writing custom integration code for each one.

When that provider raises prices, deprecates a model, or has an outage, you're stuck. Switching means rewriting your integration layer, retraining your team, and retesting everything.

This is vendor lock-in, and it's the default state of AI development today.

## What StratifyAI Does

StratifyAI is a unified layer that sits between your application and 9 LLM providers. You write code once and it works with OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, and AWS Bedrock.

**One interface. Nine providers. Zero lock-in.**

## Who It's For

- **Engineering teams** building AI-powered products who need provider flexibility without rewriting code
- **Data teams** running analysis across models to compare cost, quality, and speed
- **Operations teams** managing AI spend across providers with real-time cost tracking and budgets
- **Platform teams** providing a shared AI infrastructure layer to internal consumers

## Key Benefits

### Use the Right Model for the Job

Not every task needs the most expensive model. StratifyAI's router automatically selects the best model based on your priorities — cost, quality, speed, or a hybrid of all three. A simple question goes to a cheap, fast model. A complex analysis goes to a premium one.

### Control Costs

Every API call is tracked by token count and cost. Set budgets per provider, per session, or per user. See exactly where your AI spend goes and optimize it without guessing.

### Stay Resilient

If a provider goes down or rate-limits you, StratifyAI retries with exponential backoff and falls back to alternative models automatically. Your application stays up even when a provider doesn't.

### Cache Intelligently

Identical requests return cached responses instantly — no API call, no cost, no latency. The O(1) LRU cache with optional SQLite persistence means repeated queries are effectively free.

### Extend with MCP

The Model Context Protocol (MCP) integration lets you connect external tools — databases, search engines, file systems — directly into the AI conversation. StratifyAI includes a curated catalog of 20 MCP servers, a setup wizard, and a permission system for safe tool execution.

### Deploy Your Way

- **Python library** for direct integration
- **REST API** with WebSocket streaming for web applications
- **CLI** for scripting, testing, and interactive use
- **Svelte 5 SPA** for a full web-based chat and management interface

## What Sets It Apart

| Capability | StratifyAI | Single-Provider SDK |
|-----------|-----------|-------------------|
| Providers supported | 9 (expandable) | 1 |
| Switch providers | Change one parameter | Rewrite integration |
| Cost tracking | Built-in, real-time | Manual |
| Intelligent routing | Automatic | N/A |
| Retry + fallback | Automatic | Manual |
| Response caching | O(1) LRU + SQLite | Manual |
| MCP tool integration | Built-in server + client | N/A |
| Vision support | Unified across providers | Provider-specific |
| RAG pipeline | Included | Build your own |

## How It Works (30-Second Version)

```python
from stratifyai import LLMClient
from stratifyai.models import ChatRequest, Message

client = LLMClient()
request = ChatRequest(
    model="claude-sonnet-4-5",  # or any model from any provider
    messages=[Message(role="user", content="Summarize this report")]
)
response = await client.chat_completion(request)

print(response.content)
print(f"Cost: ${response.usage.cost_usd:.4f}")
```

To switch providers, change the model name. Everything else stays the same.

## Current State

- **9 providers** fully integrated and tested
- **877+ tests** with 85% code coverage
- **Production-ready** security hardening (API key sanitization, rate limiting, CORS, input validation)
- **CI/CD pipeline** with automated quality gates on every change
- **MCP ecosystem** complete — server, client engine, and abstraction layer

## Getting Started

- **Quick start**: [docs/GETTING-STARTED.md](GETTING-STARTED.md)
- **API reference**: [docs/API-REFERENCE.md](API-REFERENCE.md)
- **Enterprise overview**: [ENTERPRISE_README.md](../ENTERPRISE_README.md)
