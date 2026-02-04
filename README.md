
![StratumAI](stratum_logo.png)

# StratumAI — Unified Multi‑Provider LLM Interface

StratumAI is a production‑ready Python framework that provides a unified interface for 9+ LLM providers, including OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, and AWS Bedrock. It eliminates vendor lock‑in, simplifies multi‑model development, and enables intelligent routing, cost tracking, caching, streaming, and RAG workflows.

## Features

### Core
- Unified API for 9+ LLM providers
- Automatic provider detection
- Cost tracking and budget enforcement
- Retry logic with fallback models
- Streaming support for all providers
- Response caching + provider prompt caching
- Intelligent routing (cost, quality, latency, hybrid)
- Capability filtering (vision, tools, reasoning)
- Model metadata and context window awareness

### Advanced
- Large‑file handling with chunking and progressive summarization
- File extraction (CSV schema, JSON schema, logs, code structure)
- Auto model selection for extraction tasks
- RAG pipeline with embeddings + vector DB (ChromaDB)
- Semantic search and citation tracking
- Rich/Typer CLI with interactive mode
- Optional FastAPI web interface

## Installation

```bash
git clone https://github.com/Bytes0211/stratumai.git
cd stratumai
pip install -e .
```

Or using `uv`:

```bash
uv sync
```

## Configuration

```bash
cp .env.example .env
# Add your API keys
```

Check configured providers:

```bash
stratumai check-keys
```

## Quick Example

```python
from llm_abstraction import LLMClient
from llm_abstraction.models import Message

client = LLMClient()

response = client.chat(
    model="gpt-4o-mini",
    messages=[Message(role="user", content="Explain quantum computing")]
)

print(response.content)
print(response.usage.cost_usd)
```

## CLI Usage

```bash
stratumai chat -p openai -m gpt-4o-mini -t "Hello"
stratumai route "Explain relativity" --strategy hybrid
stratumai interactive
stratumai cache-stats
```

## Routing

- **Cost**: choose cheapest model
- **Quality**: choose highest‑quality model
- **Latency**: choose fastest model
- **Hybrid (default)**: dynamic weighting based on complexity

## RAG

- Embeddings (OpenAI)
- ChromaDB vector storage
- Semantic search
- Document indexing
- Retrieval‑augmented generation

## Project Structure

```
stratumai/
├── llm_abstraction/      # Core package
├── chat/                 # Provider-specific chat modules
├── cli/                  # Typer CLI
├── api/                  # Optional FastAPI server
├── examples/             # Usage examples
└── docs/                 # Technical documentation
```

## Testing

```bash
pytest
pytest -v
```

## License

Internal project — All rights reserved.
```

---

# ✅ **VERSION B — Full Enterprise Edition (Complete, Polished, Structured)**

This version keeps **all** your content but reorganizes it into a clean, markdownlint‑compliant, professional document.

```markdown
# StratumAI — Unified Intelligence Across Every Model Layer

**Status:** Phase 7.5 Complete  
**Providers:** 9 Operational  
**Features:** Routing • RAG • Caching • Streaming • CLI • Web UI

StratumAI is a production‑ready Python framework that unifies access to frontier LLM providers through a single, consistent API. It eliminates vendor lock‑in, simplifies multi‑model development, and provides intelligent routing, cost tracking, caching, streaming, and RAG capabilities.

---

## Why StratumAI Matters

Modern AI applications require flexibility across providers, models, and capabilities. StratumAI provides:

- A **single interface** for 9+ LLM providers  
- **Automatic routing** to the best model for each task  
- **Cost control** with token tracking and budgets  
- **Resilience** through retries and fallback chains  
- **Advanced workflows** including RAG, extraction, and large‑file handling  

---

## Key Skills Demonstrated

- API abstraction and design patterns (Strategy, Factory)
- Multi‑provider integration (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, AWS Bedrock)
- Production engineering (retry logic, cost tracking, caching)
- Python best practices (type hints, dataclasses, ABCs)
- Testing (unit + integration, 80%+ coverage)
- DevOps (PyPI packaging, dependency management)
- CLI engineering (Typer + Rich)
- RAG and vector database integration

---

## Core Platform Features

### Unified Interface
- One API for all providers  
- Zero code changes when switching models  
- Automatic provider detection  

### Reliability & Performance
- Retry logic with exponential backoff  
- Fallback model chains  
- Cost tracking and budget enforcement  
- Streaming support for all providers  

### Intelligence Layer
- Router with cost/quality/latency/hybrid strategies  
- Prompt complexity analysis  
- Capability filtering (vision, tools, reasoning)  
- Model metadata (context window, latency, cost)  

### Advanced Capabilities
- Response caching + provider prompt caching  
- Large‑file chunking and progressive summarization  
- File extraction (CSV, JSON, logs, code)  
- Auto model selection for extraction tasks  
- RAG pipeline with embeddings + ChromaDB  
- Semantic search and citation tracking  

---

## Architecture Overview

### Design Principles
- Abstraction first  
- Strategy pattern for providers  
- Configuration‑driven model catalogs  
- Extensible metadata and capability matrices  

### Core Components
1. **BaseProvider** — shared interface for all providers  
2. **LLMClient** — unified client with routing and detection  
3. **Router** — intelligent model selection  
4. **CostTracker** — usage and budget management  
5. **Decorators** — caching, logging, retry  
6. **Chunking & Extraction** — large‑file processing  
7. **RAG Engine** — embeddings, vector DB, retrieval  

### Request Flow

```
User
  ↓
LLMClient
  ↓
Provider Detection → Provider Implementation → LLM API
  ↓
Cost Tracking → Budget Enforcement
```

---

## Technology Stack

- **Python 3.10+**
- **OpenAI SDK**, **Anthropic SDK**, **Google Generative AI**
- **boto3** for AWS Bedrock
- **pytest**, **pytest‑cov**, **mypy**, **ruff**, **black**
- **FastAPI** (optional web UI)
- **ChromaDB** for vector storage

---

## Quick Start

### Installation

```bash
git clone https://github.com/Bytes0211/stratumai.git
cd stratumai
pip install -e .
```

Or with `uv`:

```bash
uv sync
```

### Configure API Keys

```bash
cp .env.example .env
# Add your keys
```

Check configuration:

```bash
stratumai check-keys
```

### First Chat

```bash
stratumai chat -p openai -m gpt-4o-mini -t "Hello!"
```

### Python Example

```python
from llm_abstraction import LLMClient
from llm_abstraction.models import Message

client = LLMClient()

response = client.chat(
    model="gpt-4o-mini",
    messages=[Message(role="user", content="Explain quantum computing")]
)

print(response.content)
print(response.usage.cost_usd)
```

---

## CLI Features

- Chat (streaming or non‑streaming)
- Interactive mode with file attachments
- Routing with cost/quality/latency/hybrid strategies
- Model and provider listing
- Cache inspection and clearing
- File analysis (CSV/JSON/logs/code)
- Auto model selection for extraction tasks
- RAG indexing and retrieval

---

## RAG Features

- Embeddings (OpenAI)
- ChromaDB vector storage
- Document indexing and chunking
- Semantic search
- Retrieval‑augmented generation
- Citation tracking

---

## Project Structure

```
stratumai/
├── llm_abstraction/
├── chat/
├── cli/
├── api/
├── examples/
└── docs/
```

---

## Testing

```bash
pytest
pytest -v
```

---

## License

Internal project — All rights reserved.
```

---

