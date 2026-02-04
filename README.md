# StratumAI - Unified Intelligence Across Every Model Layer

**Status:** Phase 7.5 Complete ✅ | 9 Providers Operational | AWS Bedrock Support | RAG Integration | Chat Package

## Why This Project Matters

StratumAI is a production-ready Python module that provides a unified, abstracted interface for accessing multiple frontier LLM providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, AWS Bedrock) through a consistent API. It eliminates vendor lock-in, simplifies multi-model development, and enables intelligent routing between providers.

## Key Skills Demonstrated

- **API Abstraction & Design Patterns**: Strategy pattern, factory pattern, provider abstraction
- **Multi-Provider Integration**: 9 LLM providers with unified interface (including AWS Bedrock)
- **Production Engineering**: Error handling, retry logic, cost tracking, budget management
- **Python Best Practices**: Type hints, dataclasses, abstract base classes, decorators
- **Testing & Quality**: Unit tests, integration tests, 80%+ coverage target
- **DevOps & Packaging**: PyPI package preparation, uv/pip dependency management

## Project Overview

StratumAI is a multi-provider LLM abstraction module that allows developers/users to switch between AI models from different providers without changing their code. The module provides automatic retry with fallback, cost tracking, intelligent routing, and advanced features like streaming, caching, and budget management.

### What This Project Delivers

**Core Platform:**

- **Unified Interface**: Single API for all LLM providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, AWS Bedrock)
- **Zero-Lock-In**: Switch models without code changes
- **Cost Tracking**: Automatic token usage and cost calculation per request
- **Automatic Retry**: Exponential backoff with fallback model support
- **Intelligent Router**: Select optimal model based on cost, quality, or hybrid strategies
- **Advanced Features**: Streaming, caching, logging decorators, budget limits

### Key Technical Achievements

- ✅ Project initialized with comprehensive technical design (1,232 lines)
- ✅ 7-week implementation roadmap completed
- ✅ 9 provider implementations complete (including AWS Bedrock)
- ✅ Streaming support for all providers
- ✅ Cost tracking accurate to $0.0001
- ✅ Production-ready error handling and retry logic
- ✅ Web GUI with FastAPI and interactive interface
- ✅ Intelligent routing with complexity analysis
- ✅ Rich/Typer CLI for terminal usage (Phase 5 Complete)
- ✅ Large file handling with chunking and extraction (Phase 7.1-7.2)
- ✅ Automatic model selection for file types (Phase 7.3 Complete)
- ✅ RAG/Vector DB Integration with semantic search (Phase 7.5 Complete)
- ✅ Chat package with provider-specific modules and sensible defaults

## Architecture Overview

**Design Principles:**
- **Abstraction First**: Hide provider-specific differences behind unified interface
- **Strategy Pattern**: Each provider implements common BaseProvider interface
- **Configuration-Driven**: Model catalogs, cost tables, capability matrices externalized

**Core Components:**
1. **BaseProvider**: Abstract interface that all providers implement
2. **LLMClient**: Unified client with provider detection and routing
3. **Provider Implementations**: 9 providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, AWS Bedrock)
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
- **boto3**: For AWS Bedrock models

### Development
- **Languages:** Python 3.10+
- **Package Manager:** uv (alternative: pip)
- **Testing:** pytest, pytest-cov, pytest-mock
- **Code Quality:** black (formatting), ruff (linting), mypy (type checking)
- **Version Control:** Git with conventional commits
- **Documentation:** Markdown, docstrings

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Bytes0211/stratumai.git
cd stratumai

# Install dependencies
pip install -e .

# Or using uv (recommended)
uv sync
```

### 2. Configure API Keys

**You only need keys for providers you plan to use.**

```bash
# Option 1: Use the interactive setup wizard
stratumai setup

# Option 2: Manual setup
cp .env.example .env
# Edit .env and add at least one API key
```

**Get API Keys:**
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/settings/keys
- **Google Gemini**: https://makersuite.google.com/app/apikey
- **AWS Bedrock**: https://docs.aws.amazon.com/bedrock/
- **DeepSeek**: https://platform.deepseek.com/api-docs/
- **Groq**: https://console.groq.com/keys
- **Grok (X.AI)**: https://x.ai/api
- **OpenRouter**: https://openrouter.ai/keys
- **Ollama**: https://ollama.ai/download (local, no key needed)

### 3. Verify Setup

```bash
# Check which providers are ready
stratumai check-keys

# Expected output:
# ✓ OpenAI (OPENAI_API_KEY)
# ✗ Anthropic (ANTHROPIC_API_KEY)
# ...
```

### 4. Test with a Quick Chat

```bash
# Simple chat
stratumai chat -p openai -m gpt-4o-mini -t "Hello!"

# Interactive mode (recommended for exploration)
stratumai interactive
```

### 5. Use in Your Code

```python
from llm_abstraction import LLMClient
from llm_abstraction.models import Message

# Option 1: Use environment variables (.env file)
client = LLMClient(provider="openai")

# Option 2: Pass API key explicitly
client = LLMClient(provider="openai", api_key="your-key-here")

# Make a request
response = client.chat(
    model="gpt-4o-mini",
    messages=[Message(role="user", content="Hello!")]
)

print(response.content)
print(f"Cost: ${response.usage.cost_usd:.6f}")
```

## Detailed Setup Instructions

### Prerequisites
- Python 3.10+ with venv support
- uv (recommended) or pip for package management

### Optional: Web GUI

```bash
# Install FastAPI dependencies
pip install fastapi uvicorn websockets

# Run web interface
uvicorn api.main:app --reload
# Open http://localhost:8000
```

## Project Structure

```txt
stratumai/
├── README.md
├── WARP.md
├── requirements.txt
├── .venv/
├── docs/
│   ├── project-status.md              # 6-week timeline with detailed phases
│   └── stratumai-technical-approach.md # Comprehensive technical design (1,232 lines)
├── chat/                               # Provider-specific chat modules
│   ├── __init__.py                     # Package exports (openai, anthropic, etc.)
│   ├── stratumai_openai.py             # OpenAI chat (default: gpt-4o-mini)
│   ├── stratumai_anthropic.py          # Anthropic chat (default: claude-3-5-sonnet)
│   ├── stratumai_google.py             # Google chat (default: gemini-2.5-flash)
│   ├── stratumai_deepseek.py           # DeepSeek chat (default: deepseek-chat)
│   ├── stratumai_groq.py               # Groq chat (default: llama-3.3-70b)
│   ├── stratumai_grok.py               # Grok chat (default: grok-beta)
│   ├── stratumai_openrouter.py         # OpenRouter chat (default: llama-3.3-70b:free)
│   ├── stratumai_ollama.py             # Ollama chat (default: llama3.2)
│   └── stratumai_bedrock.py            # AWS Bedrock chat (default: claude-3-5-sonnet)
├── cli/
│   └── stratumai_cli.py               # Rich/Typer CLI interface
├── api/                                # Optional FastAPI web interface
│   ├── main.py                         # FastAPI application
│   └── static/                         # Web UI files
├── examples/
│   ├── router_example.py               # Router usage examples
│   └── caching_examples.py             # Caching decorator examples
└─ llm_abstraction/                    # Main package
    ├── __init__.py
├── llm_abstraction/                    # Main package
    ├── __init__.py
    ├── client.py                       # Unified LLMClient
    ├── models.py                       # Data models (Message, ChatRequest, ChatResponse)
    ├── config.py                       # Model catalogs and cost tables
    ├── exceptions.py                   # Custom exceptions
    ├── cost_tracker.py                 # Cost tracking module
    ├── retry.py                        # Retry logic with fallbacks
    ├── caching.py                      # Response caching
    ├── router.py                       # Intelligent routing + extraction routing
    ├── chunking.py                     # Smart content chunking
    ├── summarization.py                # Progressive summarization
    ├── utils/                          # Utilities (Phase 7.1-7.3)
    │   ├── token_counter.py            # Token estimation
    │   ├── file_analyzer.py            # File type detection
    │   ├── model_selector.py           # Auto model selection (Phase 7.3)
    │   ├── csv_extractor.py            # CSV schema extraction
    │   ├── json_extractor.py           # JSON schema extraction
    │   ├── log_extractor.py            # Log error extraction
    │   └── code_extractor.py           # Code structure extraction
        ├── openai.py                   # OpenAI implementation
        ├── anthropic.py                # Anthropic implementation
        ├── google.py                   # Google Gemini implementation
        ├── deepseek.py                 # DeepSeek implementation
        ├── groq.py                     # Groq implementation
        ├── grok.py                     # Grok (X.AI) implementation
        ├── openrouter.py               # OpenRouter implementation
        ├── ollama.py                   # Ollama local models
        └── bedrock.py                  # AWS Bedrock implementation
```

## Key Features

### Core Features
- **Unified Interface**: Single API for 9 LLM providers
- **Provider Abstraction**: BaseProvider interface with consistent methods
- **Automatic Provider Detection**: Infer provider from model name
- **Cost Calculation**: Per-request token usage and cost tracking
- **Error Handling**: Custom exception hierarchy for different failure modes

### Advanced Features
- **Streaming Support**: Iterator-based streaming for all providers
- **Cost Tracker**: Call history, grouping by provider/model, budget enforcement
- **Retry Logic**: Exponential backoff with configurable fallback models
- **Caching Decorator**: Cache responses with configurable TTL
- **Logging Decorator**: Comprehensive logging of all LLM calls
- **Budget Management**: Set limits and receive alerts

### Router Features
- **Complexity Analysis**: Analyze prompt to determine appropriate model tier
- **Routing Strategies**: Cost-optimized, quality-focused, latency-focused, or hybrid
- **Model Metadata**: Context windows, capabilities, performance characteristics
- **Performance Benchmarks**: Latency, cost, and quality metrics

### CLI Features ✅
- **Rich/Typer Interface**: Beautiful terminal UI with colors, tables, and spinners
- **Core Commands**: chat, models, providers, route, interactive, analyze
- **Numbered Selection**: Choose provider/model by number instead of typing names
- **Reasoning Model Labels**: Visual indicators for reasoning models (o1, o3-mini, deepseek-reasoner)
- **Fixed Temperature Handling**: Automatic temperature setting for reasoning models
- **Enhanced Metadata Display**: Provider, Model, Context Window, Token Breakdown, Cost
- **Token Breakdown**: Separate display of input tokens, output tokens, and total tokens (In: X | Out: Y | Total: Z)
- **Spinner Feedback**: Animated "Thinking..." indicator while waiting for responses
- **Streaming Output**: Real-time LLM responses with no flicker
- **Interactive Mode**: Conversation loop with history, context display, and special commands:
  - `/file <path>` - Load and send file immediately (with intelligent extraction for large files)
  - `/attach <path>` - Stage file for next message
  - `/clear` - Clear staged attachments
  - `/save [path]` - Save last assistant response to file with metadata
  - `/provider` - Switch provider and model mid-conversation (preserves history)
  - `/help` - Display available commands and session info
  - `exit, quit, q` - Exit interactive mode
- **Intelligent File Extraction**: Automatic schema extraction for large files (>500KB)
  - CSV → Schema with statistics (26-99% token reduction)
  - JSON → Type-safe schema (78-95% reduction)
  - Logs → Error summary (90% reduction)
  - Python → AST structure (33-80% reduction)
  - User prompted to choose extraction vs. full file load
- **File Analysis**: `analyze` command extracts schemas from CSV/JSON, errors from logs, structure from code
- **Auto Model Selection**: --auto-select flag automatically chooses optimal model for file type (Phase 7.3)
- **File Attachments**: Upload files via `--file` flag or in-conversation commands
- **File Size Limits**: 5 MB max with warnings for files >500 KB
- **Conversation Persistence**: History maintained when switching providers/models
- **Response Export**: Save assistant responses as markdown files with full metadata
- **Router Integration**: Auto-select best model from CLI
- **Environment Variables**: Native support for STRATUMAI_PROVIDER, STRATUMAI_MODEL

### Large File Handling Features
- **Token Counting**: Provider-specific token estimation with tiktoken for OpenAI
- **File Analysis**: Automatic file type detection (CSV, JSON, Python, logs, etc.)
- **Smart Chunking**: Split large files at paragraph/sentence boundaries
- **Progressive Summarization**: Multi-chunk summarization with cheaper models
- **CLI Integration**: `--chunked` and `--chunk-size` flags for chat command
- **Token Warnings**: Alert when approaching model context limits (>80%)
- **Reduction Stats**: Display token reduction percentage after summarization

### RAG (Retrieval-Augmented Generation) Features ✨ NEW
- **Vector Database**: ChromaDB integration for document storage
- **Embeddings**: OpenAI text-embedding-3-small/large support with cost tracking
- **Semantic Search**: Retrieve relevant document chunks based on query similarity
- **Document Indexing**: Index single files or entire directories with automatic chunking
- **RAG Pipeline**: Complete end-to-end RAG with context retrieval and LLM generation
- **Citation Tracking**: Source attribution for all retrieved chunks
- **Collection Management**: Create, list, and delete vector database collections
- **Configurable Retrieval**: Adjust top-k results and chunk sizes
- **Example Scripts**: 4 demonstrations showing basic usage, directory indexing, retrieval-only, and collection management

## Project Status

**Current Phase:** Phase 7.5 - RAG/Vector DB Integration ✅ COMPLETE

**Progress:** Phases 1-6 Complete + Phase 7.1-7.5 Complete

**Completed Phases:**
- ✅ **Phase 1:** Core Implementation (5/5 tasks)
  - BaseProvider abstract class
  - OpenAI provider with cost tracking
  - Unified LLMClient
  - Custom exception hierarchy
  - 32 unit tests passing

- ✅ **Phase 2:** Provider Expansion (9/9 tasks)
  - Anthropic provider with Messages API
  - OpenAICompatibleProvider base class
  - Google, DeepSeek, Groq, Grok, Ollama, OpenRouter providers
  - 77 total tests passing
  - All 9 providers operational (added AWS Bedrock)

- ✅ **Phase 3:** Advanced Features (6/6 tasks)
  - Cost tracking module with analytics
  - Budget limits and alerts
  - Retry logic with exponential backoff
  - Fallback model/provider support
  - Streaming support (all providers)
  - Cache statistics tracking

- ✅ **Phase 3.5:** Web GUI (4/4 tasks)
  - FastAPI REST API
  - WebSocket streaming
  - Interactive web interface
  - Real-time cost tracking dashboard

- ✅ **Phase 4:** Router and Optimization (5/5 tasks)
  - Router with intelligent model selection
  - Complexity analysis algorithm
  - Cost/quality/latency/hybrid strategies
  - 33 router unit tests passing

- ✅ **Phase 5:** CLI Interface (4/4 tasks)
  - Typer CLI framework with Rich formatting
  - Core commands (chat, models, providers, route, interactive)
  - Numbered selection with reasoning labels
  - Enhanced metadata display and user experience
  - Markdown export functionality
  - Loop functionality for multiple queries

- ✅ **Phase 6:** Production Readiness (6/6 tasks)
  - Complete API documentation (API-REFERENCE.md, GETTING-STARTED.md)
  - 6 example applications (chatbot, code reviewer, document summarizer, performance benchmark, router examples, caching examples)
  - Performance optimization (<200ms cold start, <20MB memory)
  - Prompt caching system (response cache + provider caching)
  - CLI cache visibility and file input enhancements
  - PyPI package preparation (setup.py, pyproject.toml, MANIFEST.in)

- ✅ **Phase 7.1:** Large File Handling - Token Estimation & Chunking (5/5 tasks)
  - Token counting utility (tiktoken for OpenAI)
  - File type analysis and warnings
  - Smart chunking at natural boundaries
  - Progressive summarization with cheaper models
  - CLI integration (--chunked, --chunk-size flags)
  - 19 unit tests passing

- ✅ **Phase 7.2:** Intelligent Extraction (4/4 tasks)
  - CSV schema extraction (26-99% token reduction) - 197 lines
  - JSON schema extraction (78-95% token reduction) - 219 lines
  - Log error extraction (90% token reduction) - 267 lines
  - Code structure extraction with AST (33-80% reduction) - 327 lines
  - `analyze` CLI command for all file types
  - pandas dependency for CSV processing
  - 35 unit tests passing (100%)

- ✅ **Phase 7.3:** Model Auto-Selection (4/4 tasks)
  - ModelSelector class for file-based selection (324 lines)
  - Router.route_for_extraction() method with quality prioritization
  - --auto-select flag in chat command
  - Auto-selection in analyze command (provider/model flags)
  - ExtractionMode enum (schema/errors/structure/summary)
  - 32 unit tests passing (100%)

- ✅ **Phase 7.4:** Enhanced Caching UI (4/4 tasks)
  - Enhanced ResponseCache with hit/miss tracking and cost analytics
  - cache-stats command with --detailed flag for entry inspection
  - cache-clear command with confirmation prompt
  - Visual hit rate indicators and cost savings analysis
  - 11 unit tests passing (100%)

- ✅ **Phase 7.5:** RAG/Vector DB Integration (3/3 tasks)
  - Embeddings module with OpenAI provider (236 lines)
  - Vector database module with ChromaDB (344 lines)
  - RAG pipeline with document indexing and querying (378 lines)
  - Semantic search with configurable top-k retrieval
  - Citation tracking for source attribution
  - Example script with 4 demonstrations (287 lines)
  - ChromaDB dependency integration

**Next Steps:**
- 📝 Phase 8: Production Deployment
- 📝 PyPI package publishing
- 📝 Documentation finalization

## Usage Examples

### CLI Usage (Phase 5 - Complete ✅)
```bash
# Quick start with interactive mode
./start_app.sh

# Simple chat with command-line args
python -m cli.stratumai_cli chat "What is AI?" --provider openai --model gpt-4o-mini

# Interactive prompts (numbered selection)
python -m cli.stratumai_cli chat
# Prompts for:
# 1. Provider (1-8)
# 2. Model (numbered list with reasoning labels)
# 3. Temperature (auto-set for reasoning models)
# 4. Your message
# Then shows: Provider | Model | Context | In: X | Out: Y | Total: Z | Cost

# Streaming mode
python -m cli.stratumai_cli chat "Write a poem" --provider openai --model gpt-4o-mini --stream

# Auto-route to best model
python -m cli.stratumai_cli route "Explain quantum computing" --strategy hybrid

# Interactive conversation mode with special commands
python -m cli.stratumai_cli interactive --provider anthropic --model claude-sonnet-4-5-20250929
# Within interactive mode:
#   /file <path>     - Load and send file (auto-extracts schemas for large files)
#   /attach <path>   - Stage file for next message
#   /clear           - Clear staged files
#   /save [path]     - Save last response to file with metadata
#   /provider        - Switch provider/model (history preserved)
#   /help            - Show commands and session info
#   exit, quit, q    - Exit

# Interactive mode with initial file context
python -m cli.stratumai_cli interactive --file document.txt

# Chat with file attachment
python -m cli.stratumai_cli chat --file report.pdf --provider openai --model gpt-4o

# Chat with large file using chunking and summarization
python -m cli.stratumai_cli chat --file large_document.txt --chunked --provider openai --model gpt-4o-mini

# Chat with custom chunk size
python -m cli.stratumai_cli chat --file data.csv --chunked --chunk-size 100000 --provider openai --model gpt-4o-mini

# Analyze file structure (CSV schema, JSON schema, log errors, code structure)
python -m cli.stratumai_cli analyze data/housing.csv
# Auto-selects optimal model and shows 99.4% token reduction

# View cache statistics
python -m cli.stratumai_cli cache-stats
python -m cli.stratumai_cli cache-stats --detailed  # Show top 10 entries

# Clear response cache
python -m cli.stratumai_cli cache-clear

# List all models
python -m cli.stratumai_cli models

# List models for specific provider
python -m cli.stratumai_cli models --provider openai

# List all providers
python -m cli.stratumai_cli providers

# With environment variables
export STRATUMAI_PROVIDER=anthropic
export STRATUMAI_MODEL=claude-sonnet-4-5-20250929
python -m cli.stratumai_cli chat "Hello"
```

### Python Library Usage
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

### Chat Package Usage (Simplified API)
```python
# Provider-specific modules with sensible defaults
from chat import openai, anthropic, google, deepseek, groq

# Simple string prompt - uses default model
response = openai.chat("What is Python?")
print(response.content)

# With system prompt
response = anthropic.chat(
    "Explain quantum computing",
    system="Be concise and use analogies",
    temperature=0.5
)

# Streaming
for chunk in google.chat_stream("Tell me a story"):
    print(chunk.content, end="", flush=True)

# Override default model
response = groq.chat("Hello", model="llama-3.1-8b-instant")
```

**Default Models by Provider:**
- `openai`: gpt-4o-mini
- `anthropic`: claude-3-5-sonnet-20241022
- `google`: gemini-2.5-flash
- `deepseek`: deepseek-chat
- `groq`: llama-3.3-70b-versatile
- `grok`: grok-beta
- `openrouter`: meta-llama/llama-3.3-70b-instruct:free
- `ollama`: llama3.2
- `bedrock`: anthropic.claude-3-5-sonnet-20241022-v2:0

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

# Switch to AWS Bedrock - same interface!
response = client.chat(
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### Streaming Responses
```python
from llm_abstraction import LLMClient, ChatRequest

client = LLMClient()
request = ChatRequest(
    model="gpt-4.1-mini",
    messages=[{"role": "user", "content": "Write a poem"}]
)

for chunk in client.chat_completion_stream(request):
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

## Examples

The `examples/` directory contains 8 comprehensive real-world examples:

1. **caching_examples.py** - Response caching and cost optimization with TTL
2. **chatbot.py** - Interactive chatbot with conversation history and persistence
3. **code_reviewer.py** - Code review with multi-model comparison
4. **document_summarizer.py** - Batch document summarization with progress tracking
5. **performance_benchmark.py** - Performance benchmarking tool for latency/cost/memory
6. **router_example.py** - Intelligent model routing demonstrations
7. **rag_example.py** - RAG pipeline with vector database and semantic search
8. **web_server.py** - FastAPI server with SSE/WebSocket streaming for frontend integration

All examples are fully working and verified (✅ Feb 3, 2026):
```bash
python examples/router_example.py
python examples/chatbot.py --model gpt-4o-mini
python examples/code_reviewer.py mycode.py --compare
python examples/document_summarizer.py docs/*.txt
python examples/performance_benchmark.py --requests 5
python examples/caching_examples.py
python examples/rag_example.py

# Web server with interactive demo
uvicorn examples.web_server:app --reload --port 8000
```

## Documentation

### Core Documentation
- **README.md** - This file (project overview and setup)
- **WARP.md** - Development environment guidance and project status
- **docs/stratumai-technical-approach.md** - Comprehensive technical design (1,232 lines)
- **docs/project-status.md** - Detailed implementation timeline
- **docs/frontend-integration.md** - Guide for integrating StratumAI with web frontends (SSE/WebSocket)

## Testing

The project has comprehensive test coverage:
- **Unit Tests**: 77+ tests for core functionality
- **Integration Tests**: Provider-specific tests for all 9 providers
- **Router Tests**: 33 tests for intelligent model selection
- **Phase 7.1 Tests**: 19 tests for token counting, chunking, and summarization

Run tests with:
```bash
pytest                    # Run all tests
pytest -v                 # Verbose output
pytest tests/test_*.py    # Specific test file
```

## License

Internal project - All rights reserved

## Contact

Project Owner: scotton
