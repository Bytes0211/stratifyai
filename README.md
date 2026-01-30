# StratumAI - Unified Intelligence Across Every Model Layer

## Why This Project Matters

StratumAI is a production-ready Python module that provides a unified, abstracted interface for accessing multiple frontier LLM providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama) through a consistent API. It eliminates vendor lock-in, simplifies multi-model development, and enables intelligent routing between providers.

## Key Skills Demonstrated

- **API Abstraction & Design Patterns**: Strategy pattern, factory pattern, provider abstraction
- **Multi-Provider Integration**: 8 LLM providers with unified interface
- **Production Engineering**: Error handling, retry logic, cost tracking, budget management
- **Python Best Practices**: Type hints, dataclasses, abstract base classes, decorators
- **Testing & Quality**: Unit tests, integration tests, 80%+ coverage target
- **DevOps & Packaging**: PyPI package preparation, uv/pip dependency management

## Project Overview

StratumAI is a multi-provider LLM abstraction module that allows developers to switch between AI models from different providers without changing their code. The module provides automatic retry with fallback, cost tracking, intelligent routing, and advanced features like streaming, caching, and budget management.

### What This Project Delivers

**Core Platform:**

- **Unified Interface**: Single API for all LLM providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama)
- **Zero-Lock-In**: Switch models without code changes
- **Cost Tracking**: Automatic token usage and cost calculation per request
- **Automatic Retry**: Exponential backoff with fallback model support
- **Intelligent Router**: Select optimal model based on cost, quality, or hybrid strategies
- **Advanced Features**: Streaming, caching, logging decorators, budget limits

### Key Technical Achievements

- ✅ Project initialized with comprehensive technical design (1,232 lines)
- ✅ 5-week implementation roadmap (25 working days)
- 📝 8 provider implementations planned
- 📝 Streaming support for all providers
- 📝 Cost tracking accurate to $0.0001
- 📝 Intelligent routing with complexity analysis
- 📝 Production-ready error handling and retry logic

## Architecture Overview

**Design Principles:**
- **Abstraction First**: Hide provider-specific differences behind unified interface
- **Strategy Pattern**: Each provider implements common BaseProvider interface
- **Configuration-Driven**: Model catalogs, cost tables, capability matrices externalized

**Core Components:**
1. **BaseProvider**: Abstract interface that all providers implement
2. **LLMClient**: Unified client with provider detection and routing
3. **Provider Implementations**: 8 providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama)
4. **Cost Tracker**: Track usage and enforce budget limits
5. **Router**: Intelligent model selection based on complexity analysis
6. **Decorators**: Logging, caching, retry utilities

**Request Flow:**
```
User → LLMClient → Provider Detection → Provider Implementation → LLM API
                                      ↓
                                Cost Tracking → Budget Check
```

## Technology Stack

### Core Technologies
- **Python 3.10+**: Core language with type hints
- **OpenAI SDK**: For OpenAI and OpenAI-compatible providers
- **Anthropic SDK**: For Claude models
- **Google Generative AI SDK**: For Gemini models

### Development
- **Languages:** Python 3.10+
- **Package Manager:** uv (alternative: pip)
- **Testing:** pytest, pytest-cov, pytest-mock
- **Code Quality:** black (formatting), ruff (linting), mypy (type checking)
- **Version Control:** Git with conventional commits
- **Documentation:** Markdown, docstrings

## Setup Instructions

### Prerequisites
- Python 3.12+ with venv support
- [Other prerequisites]

### Initial Setup

1. **Create virtual environment and install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **[Additional setup steps]:**
   ```bash
   # Add setup commands
   ```

## Project Structure

```txt
stratumai/
├── README.md
├── WARP.md
├── requirements.txt
├── .venv/
├── docs/
│   ├── project-status.md              # 5-week timeline with detailed phases
│   └── stratumai-technical-approach.md # Comprehensive technical design (1,232 lines)
└── llm_abstraction/                    # Main package (to be implemented)
    ├── __init__.py
    ├── client.py                       # Unified LLMClient
    ├── models.py                       # Data models (Message, ChatRequest, ChatResponse)
    ├── config.py                       # Model catalogs and cost tables
    ├── exceptions.py                   # Custom exceptions
    ├── utils.py                        # Helper functions
    ├── router.py                       # Intelligent routing
    └── providers/
        ├── base.py                     # BaseProvider abstract class
        ├── openai.py                   # OpenAI implementation
        ├── anthropic.py                # Anthropic implementation
        ├── google.py                   # Google Gemini implementation
        ├── deepseek.py                 # DeepSeek implementation
        ├── groq.py                     # Groq implementation
        ├── grok.py                     # Grok (X.AI) implementation
        ├── openrouter.py               # OpenRouter implementation
        └── ollama.py                   # Ollama local models
```

## Key Features

### Core Features (Phase 1-2)
- **Unified Interface**: Single API for 8 LLM providers
- **Provider Abstraction**: BaseProvider interface with consistent methods
- **Automatic Provider Detection**: Infer provider from model name
- **Cost Calculation**: Per-request token usage and cost tracking
- **Error Handling**: Custom exception hierarchy for different failure modes

### Advanced Features (Phase 3)
- **Streaming Support**: Iterator-based streaming for all providers
- **Cost Tracker**: Call history, grouping by provider/model, budget enforcement
- **Retry Logic**: Exponential backoff with configurable fallback models
- **Caching Decorator**: Cache responses with configurable TTL
- **Logging Decorator**: Comprehensive logging of all LLM calls
- **Budget Management**: Set limits and receive alerts

### Router Features (Phase 4)
- **Complexity Analysis**: Analyze prompt to determine appropriate model tier
- **Routing Strategies**: Cost-optimized, quality-focused, or hybrid
- **Model Metadata**: Context windows, capabilities, performance characteristics
- **Performance Benchmarks**: Latency, cost, and quality metrics

## Project Status

**Current Phase:** Phase 1 - Core Implementation (Week 1)

**Progress:** 4% Complete (Day 1 of 25 complete)

**Completed:**
- ✅ Project initialized with uv
- ✅ Virtual environment created
- ✅ Documentation structure established
- ✅ Technical approach document created (1,232 lines)
- ✅ 5-week implementation roadmap defined

**In Progress:**
- ⚙️ Phase 1: Core Implementation (20% complete)
  - Day 1: ✅ Project setup + technical design
  - Day 2: 📝 Base provider interface
  - Day 3: 📝 OpenAI provider implementation
  - Day 4: 📝 Unified client implementation
  - Day 5: 📝 Error handling + unit tests

**Next Steps:**
- 📝 Implement BaseProvider abstract class
- 📝 Create data models (Message, ChatRequest, ChatResponse, Usage)
- 📝 Implement OpenAI provider with cost tracking
- 📝 Build unified LLMClient with provider registry
- 📝 Create custom exception hierarchy
- 📝 Write unit tests for core components

## Usage Examples

### Basic Usage
```python
from llm_abstraction import LLMClient

# Initialize client (reads API keys from environment)
client = LLMClient()

# Simple chat completion
response = client.chat(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": "Explain quantum computing"}],
    temperature=0.7
)

print(response.content)
print(f"Cost: ${response.usage.cost_usd:.4f}")
```

### Switching Models (No Code Changes)
```python
# Switch to Anthropic - same interface!
response = client.chat(
    model="claude-sonnet-4-5-20250929",
    messages=[{"role": "user", "content": "Hello!"}]
)

# Switch to Google - still same interface!
response = client.chat(
    model="gemini-2.5-flash-lite",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Streaming Responses
```python
for chunk in client.chat_stream(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": "Write a poem"}]
):
    print(chunk.content, end="", flush=True)
```

### With Cost Tracking
```python
from llm_abstraction import LLMClient, CostTracker

client = LLMClient()
tracker = CostTracker(budget_limit=10.0)

for i in range(10):
    response = client.chat(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": f"Question {i}"}]
    )
    tracker.record_call(response.model, response.provider, response.usage)

print(tracker.get_summary())
```

## Implementation Timeline

**Total Duration:** 5 weeks (25 working days)

- **Week 1 (Jan 30 - Feb 5):** Core Implementation - BaseProvider, OpenAI, unified client
- **Week 2 (Feb 6-12):** Provider Expansion - All 8 providers operational
- **Week 3 (Feb 13-19):** Advanced Features - Streaming, cost tracking, retry logic
- **Week 4 (Feb 20-26):** Router and Optimization - Intelligent model selection
- **Week 5 (Feb 27 - Mar 5):** Production Readiness - Documentation, examples, PyPI package

**Target Completion:** March 5, 2026

## Documentation

### Core Documentation
- **README.md** - This file (project overview and setup)
- **docs/project-status.md** - Detailed 5-week timeline with phase breakdowns
- **docs/stratumai-technical-approach.md** - Comprehensive technical design (1,232 lines)
- **WARP.md** - Development environment guidance for Warp AI

## License

Internal project - All rights reserved

## Contact

Project Owner: scotton