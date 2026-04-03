# AGENTS.md

This file provides guidance to AI agents (Warp, Cursor, Windsurf, etc.) when working with code in this repository.

## Agent Operating Rules

- Always use `uv` for Python environment and dependency management workflows.
- Never run `git add`, `git commit`, or `git push`.

## Project Overview

StratifyAI is a production-ready Python framework that provides a unified, abstracted interface for accessing multiple frontier LLM providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, AWS Bedrock) through a consistent API. The project demonstrates advanced API abstraction, design patterns (strategy, factory, builder), multi-provider integration, production engineering (error handling, retry logic, cost tracking), and Python best practices (type hints, abstract base classes, async-first, decorators).

## Development Environment Setup

### Initial Setup
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Using uv (Preferred)
```bash
# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install all dependencies with uv
uv sync
# or:
uv pip install -r requirements.txt        # runtime only
uv pip install -r requirements-dev.txt     # runtime + dev/test
```

### AWS Bedrock Setup

For using AWS Bedrock models, you need to configure AWS credentials:

**Option 1: Environment Variables**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"  # Optional, defaults to us-east-1
```

**Option 2: AWS Credentials File**
```bash
# Configure AWS CLI (creates ~/.aws/credentials)
aws configure

# Or manually create ~/.aws/credentials:
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = your-access-key-id
aws_secret_access_key = your-secret-access-key
EOF
```

**Option 3: IAM Roles** (when running on AWS EC2/ECS/Lambda)
- No explicit credentials needed
- boto3 automatically uses the instance's IAM role

**Supported Bedrock Models:**
- Anthropic Claude: `anthropic.claude-3-5-sonnet-20241022-v2:0`, `anthropic.claude-3-5-haiku-20241022-v1:0`
- Meta Llama: `meta.llama3-3-70b-instruct-v1:0`, `meta.llama3-2-90b-instruct-v1:0`
- Mistral AI: `mistral.mistral-large-2402-v1:0`, `mistral.mistral-small-2402-v1:0`
- Amazon Nova: `amazon.nova-pro-v1:0`, `amazon.nova-lite-v1:0`, `amazon.nova-micro-v1:0`
- Cohere: `cohere.command-r-plus-v1:0`, `cohere.command-r-v1:0`

**Permissions Required:**
Your AWS IAM user/role must have the `bedrock:InvokeModel` permission:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
    "Resource": "*"
  }]
}
```

## Project Structure

```txt
stratifyai/                             # Project root
├── README.md                           # Project overview and quick start
├── AGENTS.md                           # This file (AI agent guidance)
├── ENTERPRISE_README.md                # Enterprise-focused documentation
├── pyproject.toml                      # Package configuration and dependencies
├── setup.py                            # Legacy setuptools entry
├── requirements.txt                    # Python runtime dependencies
├── requirements-dev.txt                # Dev/test dependencies (pytest, ruff, mypy, etc.)
├── uv.lock                             # uv locked dependency versions
├── start_app.sh                        # Convenience script to start API server
├── .venv/                              # Virtual environment (git-ignored)
├── .github/
│   └── workflows/
│       └── validate-catalog.yml        # Catalog validation CI on PRs
├── api/                                # FastAPI REST API + WebSocket
│   ├── __init__.py
│   ├── main.py                         # API endpoints, WebSocket streaming
│   └── static/
│       ├── dist/                       # Built SPA (output of `npm run build`)
│       └── index.html                  # Legacy fallback
├── frontend/                           # Svelte 5 SPA
│   ├── src/
│   │   ├── App.svelte                  # Root app component (tabbed layout)
│   │   ├── main.ts                     # SPA entry point
│   │   ├── lib/
│   │   │   ├── api/
│   │   │   │   ├── client.ts           # REST API client
│   │   │   │   ├── types.ts            # TypeScript type definitions
│   │   │   │   └── websocket.ts        # WebSocket streaming client
│   │   │   ├── components/
│   │   │   │   ├── catalog/            # ModelCatalog, ModelCard, ModelFilters, CapabilityBadge
│   │   │   │   ├── chat/               # ChatContainer, ChatHistory, ChatInput, ChatMessage, MarkdownRenderer, StreamingIndicator
│   │   │   │   ├── config/             # ModelSelector, FileUpload, ProviderBadge, TemperatureSlider, TokenConfig
│   │   │   │   ├── dashboard/          # CostSummary
│   │   │   │   ├── layout/             # AppShell, Header, Sidebar
│   │   │   │   └── shared/             # Badge, Button, LoadingSpinner, ThemeToggle
│   │   │   ├── stores/
│   │   │   │   ├── chat.ts             # Chat message state
│   │   │   │   ├── config.ts           # Provider/model configuration
│   │   │   │   ├── cost.ts             # Cost tracking state
│   │   │   │   ├── file.ts             # File attachment state
│   │   │   │   └── theme.ts            # Dark/light theme persistence
│   │   │   └── utils/
│   │   │       └── format.ts           # Formatting utilities
│   │   ├── styles/                     # SCSS (_base, _mixins, _reset, _themes, _tokens, main)
│   │   └── vite-env.d.ts               # Vite TypeScript definitions
│   ├── index.html                      # HTML entry template
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   └── vite.config.ts
├── catalog/                            # Model catalog (community-editable)
│   ├── models.json                     # Provider model metadata
│   ├── schema.json                     # JSON schema for catalog validation
│   └── README.md                       # Catalog contribution guidelines
├── cli/
│   ├── __init__.py
│   └── stratifyai_cli.py               # Typer CLI (chat, route, interactive, analyze, cache-stats, cache-clear, check-keys)
├── docs/                               # Documentation (see Documentation section)
├── examples/
│   ├── auto_selection_demo.py
│   ├── caching_examples.py
│   ├── chatbot.py
│   ├── code_reviewer.py
│   ├── document_summarizer.py
│   ├── performance_benchmark.py
│   ├── rag_example.py
│   ├── router_example.py
│   └── web_server.py
├── scripts/
│   └── validate_catalog.py             # Catalog validation tool (schema + content checks)
├── tests/                              # Test suite (536+ tests)
│   ├── conftest.py                     # Shared fixtures (provider pool cleanup)
│   ├── test_async_operations.py
│   ├── test_bedrock_provider.py
│   ├── test_caching.py
│   ├── test_chat_builder.py
│   ├── test_cli_auth_error.py
│   ├── test_cli_chat.py
│   ├── test_cli_file_loading.py
│   ├── test_client.py
│   ├── test_middleware.py              # TrackedLLMClient middleware tests
│   ├── test_model_selector.py
│   ├── test_models.py
│   ├── test_openai_provider.py
│   ├── test_persistent_cache.py        # PersistentResponseCache (SQLite) tests
│   ├── test_phase71.py
│   ├── test_phase72_extractors.py
│   ├── test_phase74_caching.py
│   ├── test_phase83_new.py             # Provider pooling & ChatResponse.to_dict tests
│   ├── test_prompts.py                 # Prompt template system tests (30 tests)
│   ├── test_providers_phase2.py
│   ├── test_router.py
│   ├── test_router_extraction.py
│   ├── test_temperature_unit.py
│   └── test_temperature_validation.py
└── stratifyai/                         # Main Python package
    ├── __init__.py                     # Package exports (LLMClient, Router, etc.)
    ├── api_key_helper.py               # API key discovery and validation
    ├── catalog_manager.py              # Loads/caches models from catalog/models.json
    ├── caching.py                      # Response caching (in-memory + SQLite persistent)
    ├── chunking.py                     # Smart text chunking at natural boundaries
    ├── client.py                       # Unified LLMClient with provider connection pooling
    ├── config.py                       # Configuration loading via catalog_manager
    ├── cost_tracker.py                 # Cost tracking with history and budgets
    ├── embeddings.py                   # Embeddings module (OpenAI provider)
    ├── exceptions.py                   # Custom exception hierarchy
    ├── logging_config.py               # Structured logging (JSON + human formatters)
    ├── middleware.py                    # TrackedLLMClient (budget, latency, cost tracking)
    ├── models.py                       # Data models: Message, ChatRequest, ChatResponse
    ├── rag.py                          # RAG pipeline with document indexing and querying
    ├── retry.py                        # Retry logic with exponential backoff (async)
    ├── router.py                       # Intelligent routing (cost/quality/latency/hybrid)
    ├── summarization.py                # Progressive summarization for large files
    ├── vectordb.py                     # ChromaDB vector store integration
    ├── chat/                           # Provider-specific chat modules (simplified API)
    │   ├── __init__.py                 # Package exports with provider aliases
    │   ├── builder.py                  # ChatBuilder for fluent configuration chaining
    │   ├── stratifyai_openai.py
    │   ├── stratifyai_anthropic.py
    │   ├── stratifyai_google.py
    │   ├── stratifyai_deepseek.py
    │   ├── stratifyai_groq.py
    │   ├── stratifyai_grok.py
    │   ├── stratifyai_openrouter.py
    │   ├── stratifyai_ollama.py
    │   └── stratifyai_bedrock.py
    ├── providers/                      # Provider strategy implementations
    │   ├── __init__.py
    │   ├── base.py                     # BaseProvider abstract class
    │   ├── openai_compatible.py        # Shared base for OpenAI-compatible providers
    │   ├── openai.py
    │   ├── anthropic.py
    │   ├── google.py
    │   ├── deepseek.py
    │   ├── groq.py
    │   ├── grok.py
    │   ├── openrouter.py
    │   ├── ollama.py
    │   └── bedrock.py
    ├── profiles/                       # Profile configuration system
    │   ├── models.py                   # Profile, ProfileParameter, PARAMETER_DEFINITIONS
    │   └── profiles.yaml               # 6 built-in profiles (fast, balanced, reasoning, vision, json, cheap)
    ├── prompts/                        # Prompt template system
    │   ├── __init__.py                 # Package exports + singleton registry
    │   ├── models.py                   # PromptTemplate, PromptParameter dataclasses
    │   ├── registry.py                 # PromptRegistry for discovery and loading
    │   └── templates/                  # Built-in YAML templates (10 templates)
    │       ├── code_review.yaml
    │       ├── summarize.yaml
    │       ├── chatbot.yaml
    │       ├── explain_concept.yaml
    │       ├── analyze_data.yaml
    │       ├── rag_synthesis.yaml
    │       ├── translate.yaml
    │       ├── debug_error.yaml
    │       ├── commit_message.yaml
    │       └── api_docs.yaml
    └── utils/
        ├── __init__.py
        ├── bedrock_validator.py        # Bedrock model availability validation
        ├── code_extractor.py           # Code structure extractor (33-80% reduction)
        ├── csv_extractor.py            # CSV schema extractor (26-99% reduction)
        ├── file_analyzer.py            # File type analysis with size warnings
        ├── json_extractor.py           # JSON schema extractor (78-95% reduction)
        ├── log_extractor.py            # Log error extractor (90% reduction)
        ├── model_selector.py           # ModelSelector for file-based auto-selection
        ├── provider_validator.py       # Provider model availability validation
        ├── reasoning_detector.py       # Detects reasoning/thinking models
        └── token_counter.py            # Token counting with tiktoken
```

## Testing

### Running Tests
```bash
# Run full test suite
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_client.py

# Run specific test
pytest tests/test_client.py::test_function_name

# Exclude slow/integration tests
pytest -m "not slow and not integration"

# Run with coverage
pytest --cov=stratifyai --cov-report=term-missing
```

## Web UI

### Quick Start
```bash
# Build frontend SPA
cd frontend && npm install && npm run build && cd ..

# Start API server (serves built SPA at /)
uvicorn api.main:app --reload --port 8080
# or use the convenience script:
./start_app.sh
```

### Development Mode
```bash
# Terminal 1: Backend
uvicorn api.main:app --reload --port 8080

# Terminal 2: Frontend dev server (with HMR)
cd frontend && npm run dev
```

## Common Workflows

### Starting Development
```bash
# Activate virtual environment
source .venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt
```

### Adding Dependencies
```bash
# Install new package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt
# or with uv:
uv add package-name
```

### CLI Quick Reference
```bash
stratifyai chat -p openai -m gpt-4o-mini -t "Hello"
stratifyai route "Explain relativity" --strategy hybrid
stratifyai interactive
stratifyai analyze path/to/file.csv
stratifyai cache-stats --detailed
stratifyai cache-clear
stratifyai check-keys
```

## Architecture Principles

**Design Principles:**
- **Abstraction First**: Hide provider-specific differences behind unified interface
- **Strategy Pattern**: Each provider implements common BaseProvider interface
- **Builder Pattern**: ChatBuilder enables fluent, reusable configuration chaining
- **Configuration-Driven**: Model catalog, cost tables, capability matrices externalized in `catalog/models.json`
- **Fail-Safe**: Automatic retry with exponential backoff and fallback models
- **Cost-Aware**: Track every token and enforce budget limits

### Key Design Decisions
1. **Async-First Architecture**: All provider methods are async using native SDK async clients (AsyncOpenAI, AsyncAnthropic, aioboto3)
2. **Provider Strategy Pattern**: All providers inherit from `BaseProvider` abstract class
3. **OpenAI-Compatible Pattern**: Providers with OpenAI-compatible APIs (Gemini, DeepSeek, Groq, Grok, Ollama, OpenRouter) share `OpenAICompatibleProvider` base class
4. **Unified Message Format**: All providers use OpenAI-compatible message format internally
5. **Cost Tracking**: Every request calculates cost based on provider-specific pricing tables
6. **Type Safety**: Full type hints and dataclasses for all requests/responses
7. **Lazy Provider Loading**: Providers are instantiated on-demand, not at client initialization
8. **Router Independence**: Router is optional — core functionality works without it
9. **Sync Wrappers**: Convenience sync methods (`chat_sync()`, `chat_completion_sync()`) for CLI and simple scripts
10. **Model Required**: All chat modules require an explicit `model` parameter — no defaults

## Project Status

**Current Phase:** MCP Implementation Planning (post-Phase 15)
**Progress:** Phases 1-15 complete; MCP technical approach finalized for execution
**Latest Updates:** Phase 14 DX + Phase 15 Security complete (Apr 2, 2026); MCP technical approach authored in `developer/PRD-MCP-implemenation.md`
**Test Suite:** 536 passed, 4 skipped

### Completed Phases
- Note: test counts listed below are phase-local historical snapshots; current suite totals are tracked in the Project Status section above.

- ✅ Phase 1: Core Implementation (100%)
  - BaseProvider abstract class
  - OpenAI provider with cost tracking
  - Unified LLMClient
  - Custom exception hierarchy
  - Historical snapshot at phase completion: 32 unit tests passing
- ✅ Phase 2: Provider Expansion (100%)
  - Anthropic provider with Messages API
  - OpenAICompatibleProvider base class
  - Google, DeepSeek, Groq, Grok, Ollama, OpenRouter providers
  - All 9 providers operational (added AWS Bedrock)
  - Historical snapshot at phase completion: 77 total tests passing
- ✅ Phase 3: Advanced Features (100%)
  - Enhanced streaming support
  - Cost tracking module with history
  - Retry logic with exponential backoff
  - Caching and logging decorators
  - Budget management system
- ✅ Phase 3.5: Web GUI (100%)
  - FastAPI REST API with endpoints
  - WebSocket streaming support
  - Interactive frontend interface
  - API documentation and tests
- ✅ Phase 4: Router and Optimization (100%)
  - Router with intelligent model selection
  - Complexity analysis algorithm
  - Cost/quality/latency/hybrid strategies
  - Fallback chain routing for resilient applications
  - Capability-based filtering (vision, tools, reasoning)
  - Historical snapshot at phase completion: 33 router unit tests passing
- ✅ Phase 5: CLI Interface (100%)
  - Typer CLI framework with 5 commands
  - Rich formatting (tables, colors, progress)
  - Environment variable support
  - Interactive mode with conversation history
  - Router integration with --capability flag
  - Streaming without flicker
  - CLI usage documentation (445 lines)
- ✅ Phase 6: Production Readiness (100%)
  - Complete API documentation
  - 6 example applications
  - Performance optimization
  - Prompt caching system
  - PyPI package preparation
- ✅ Phase 7.1: Large File Handling - Token Estimation & Chunking (100%)
  - Token counting utility with tiktoken (186 lines)
  - File type analyzer with warnings (192 lines)
  - Smart chunking at natural boundaries (158 lines)
  - Progressive summarization (179 lines)
  - CLI integration (--chunked, --chunk-size flags)
  - Historical snapshot at phase completion: 19 unit tests passing (16 passing, 3 skipped)
- ✅ Phase 7.2: Intelligent Extraction (100%)
  - CSV schema extractor (197 lines, 26-99% reduction)
  - JSON schema extractor (219 lines, 78-95% reduction)
  - Log error extractor (267 lines, 90% reduction)
  - Code structure extractor (327 lines, 33-80% reduction)
  - `analyze` CLI command
  - pandas dependency
  - Historical snapshot at phase completion: 35 unit tests passing
- ✅ Phase 7.3: Model Auto-Selection (100%)
  - ModelSelector class for file-based selection (324 lines)
  - Router.route_for_extraction() method with quality prioritization
  - --auto-select flag in chat command
  - Auto-selection in analyze command (provider/model flags)
  - ExtractionMode enum (schema/errors/structure/summary)
  - CSV → Claude Sonnet, JSON → Claude Sonnet, Logs → DeepSeek Reasoner, Code → DeepSeek
  - Historical snapshot at phase completion: 32 unit tests passing
- ✅ Phase 7.4: Enhanced Caching UI (100%)
  - Enhanced ResponseCache with hit/miss tracking and cost analytics
  - cache-stats command with --detailed flag for entry inspection
  - cache-clear command with confirmation prompt
  - Visual hit rate indicators (🎯 ≥75%, ⚠️ ≥50%, 📉 <50%)
  - Cost savings analysis showing total saved and average per hit
  - Top 10 cache entries table when --detailed flag used
  - Historical snapshot at phase completion: 11 unit tests passing
- ✅ Interactive Mode Enhancements (100%)
  - Intelligent file extraction integrated into /file and /attach commands
  - Automatic schema extraction for large files (>500KB) with user prompt
  - /save command to export assistant responses with metadata
  - Smart default filenames with timestamps (response_provider_model_timestamp.md)
  - Full metadata in saved files (provider, model, tokens, cost, timestamp)
- ✅ Phase 7.5: RAG/Vector DB Integration (100%)
  - Embeddings module with OpenAI provider (236 lines)
  - Vector database module with ChromaDB (344 lines)
  - RAG pipeline with document indexing and querying (378 lines)
  - Semantic search with configurable top-k retrieval
  - Citation tracking for source attribution
  - Example script with 4 demonstrations (287 lines)
  - ChromaDB dependency integration
- ✅ Phase 7.6: Chat Package (100%)
  - Provider-specific chat modules (9 modules)
  - Simplified API: `chat(prompt)` and `chat_stream(prompt)`
  - Optional system prompt, temperature, max_tokens parameters
  - Lazy client initialization for efficiency
  - Package exports with convenient aliases (openai, anthropic, etc.)
- ✅ Phase 7.7: Async-First Conversion (100%)
  - All providers converted to async using native SDK clients
  - AsyncOpenAI, AsyncAnthropic for primary providers
  - aioboto3 for AWS Bedrock async support
  - AsyncIterator for streaming responses
  - Sync wrappers (chat_sync, chat_completion_sync) for convenience
  - Retry decorator updated for async with asyncio.sleep
  - Cache decorator updated for async functions
  - Embeddings and RAG modules converted to async
  - Chat package modules all async with sync wrappers
  - FastAPI endpoints using native async providers
  - pytest-asyncio configuration added
  - Latency tracking (latency_ms) added to ChatResponse
  - CLI displays latency in response metadata
- ✅ Phase 7.8: Builder Pattern & Required Model (100%)
  - ChatBuilder class for fluent configuration chaining
  - Builder methods: with_model(), with_system(), with_developer(), with_temperature(), with_max_tokens(), with_options()
  - Model parameter now required (no defaults) - explicit over implicit
  - All 9 chat modules updated to require model parameter
  - chat() raises ValueError if model not specified
  - Historical snapshot at phase completion: 28 builder + 13 async operations unit tests passing
- ✅ Phase 7.9: Web UI Enhancements (100%)
  - Vision support for image uploads (GPT-4o, Claude, Gemini, Nova)
  - Dynamic file input based on model vision capability
  - Smart chunking with configurable chunk size (10k-100k chars)
  - Markdown rendering with marked.js for assistant responses
  - Syntax highlighting with highlight.js (190+ languages)
  - Model metadata display (context window, validation status)
  - Category-based model grouping in dropdowns
  - Temperature auto-disable for reasoning models
- ✅ Phase 7.10: Catalog Modernization & Auto-Sync (100%)
  - Externalized model catalog to catalog/models.json (JSON format)
  - catalog_manager.py for loading/caching catalog with deprecation tracking
  - JSON schema validation (catalog/schema.json)
  - Community contribution guidelines (catalog/README.md)
  - Enhanced Anthropic validator using models.list() API
  - Automated catalog validation in CI (.github/workflows/validate-catalog.yml)
  - Deprecation fields (deprecated, deprecated_date, replacement_model)
  - All models use dated IDs (e.g., claude-3-haiku-20240307)
  - Fixed bug: Smart chunking 404 error (updated to real model)
  - Validation script (scripts/validate_catalog.py) with schema checks
  - 7 new files, 3 modified files, ~980 lines of infrastructure
- ✅ Phase 7.11: Svelte 5 SPA (100%) - Feb 16, 2026
  - Complete rewrite with Svelte 5 (48 files, ~8,500 lines)
  - **Tabbed Interface**: Config, Files, History, Cost tracking
  - **Real-time Streaming**: WebSocket-based with live token display
  - **File Attachments**: Text files and images (vision models)
  - **Smart Chunking**: Configurable 10k-100k chars for large files
  - **Model Catalog Browser**: Filter by provider, capability badges
  - **Markdown Rendering**: Syntax highlighting (highlight.js, 190+ languages)
  - **Cost Tracking**: Real-time analytics per message and session
  - **Theme Toggle**: Dark/light with localStorage persistence
  - **Type Safety**: Full TypeScript types matching backend
  - **Security**: XSS protection (DOMPurify), image validation
  - **Client-side Routing**: SPA navigation with Vite build
  - **State Management**: Svelte stores for chat, config, cost, files
  - Dependencies: Svelte 5, Vite 6, TypeScript, marked, highlight.js, DOMPurify

- ✅ Phase 9.1: Prompt Templates (100%) - Feb 27, 2026
  - PromptTemplate and PromptParameter data models (~170 lines)
  - PromptRegistry for discovery and loading (~230 lines)
  - 10 built-in YAML templates (code_review, summarize, chatbot, etc.)
  - ChatBuilder.with_template() integration
  - CLI: templates command + --template/--params flags
  - API: /api/templates endpoints (list, get, render)
  - User-defined templates: ~/.stratifyai/prompts/
  - Full documentation (docs/PROMPT-TEMPLATES.md)
  - Historical snapshot at phase completion: 30 unit tests passing

- ✅ Phase 10: CI/CD & Testing Infrastructure (100%)
  - Full PR/push CI workflow for tests
  - Ruff format/lint and Mypy quality gates
  - Integration tests lane with marker and secret gating
  - Coverage reporting with minimum threshold
  - Frontend build artifacts removed from source control and built in CI

- ✅ Phase 11: Error Handling & Validation Hardening (100%) - Feb 2026
  - Fail-fast API key validation at client initialization
  - Client-level reasoning model temperature validation
  - Retry consistency across all request paths
  - Provider-specific timeout controls
  - Cancellation support for long-running async operations
  - Historical snapshot at phase completion: 498 tests passing, 69% coverage maintained

- ✅ Phase 12: Observability & Streaming Telemetry (100%) - Apr 1, 2026
  - Correlation ID context management across requests
  - HTTP tracing middleware with request/response latency
  - Provider health endpoints: `/health/providers`, `/api/health/providers`
  - Structured metrics export: `/api/metrics`
  - Streaming telemetry: correlation ID, first-token latency, total latency
  - Cache hit/miss/expired logging with TTL tracking
  - TrackedLLMClient middleware for pre/post-request observability
  - Historical snapshot at phase completion: 515 tests passing, 69% coverage maintained

- ✅ Phase 13: Performance & Scalability (100%) - Apr 2, 2026
  - **Objective 1: O(1) Cache Backend** - LRUCache + RWLockFair
    - Replaced O(n) min() eviction with O(1) doubly-linked list (cachetools.LRUCache)
    - RWLock: multiple concurrent readers, exclusive writers (readerwriterlock)
    - All mutations (hits, cost_saved, misses) under write lock only
    - SQLite WAL mode: PRAGMA journal_mode=WAL for concurrent reader support
    - 17 new tests (9 LRU + 8 WAL) — all passing
  - **Objective 2: Provider Concurrency Limits** - Per-provider semaphores
    - Lazy asyncio.Semaphore creation (binds to correct event loop)
    - All 9 providers implement acquire/try/finally/release pattern
    - LLMClient API: `set_provider_concurrency_limit("openai", 5)`
    - 10 new tests — semaphore, queueing, parallelism
  - **Objective 3: Load Profile Benchmarking** - 4 profiles
    - `BASELINE`, `CONCURRENT_LIGHT`, `CONCURRENT_HEAVY`, `MIXED_COMPLEXITY`
    - CLI: `python examples/performance_benchmark.py --profile concurrent-heavy`
  - **Bug fix pass** (Apr 2, 2026):
    - Fixed RWLock violation: writes inside read lock caused data corruption
    - Fixed NameError in cache_response() decorator
    - Fixed silent exception swallowing in streaming retry
    - Replaced hash()-based pool key with SHA-256 (stable across processes)
    - Removed exception-swallowing in tests, generous timing thresholds
  - Historical snapshot at phase completion: **526 total tests passing**, 69% coverage, **no regressions**
  - All 22 critical bugs identified & fixed (provider coverage, cache semantics, event loop binding, test quality)
  - See `developer/developer-journal.md` + `developer/TODO.md` for detailed summary

### In Progress

- 🔧 MCP Server Implementation Planning and Sequencing
  - Technical approach finalized with phased rollout and acceptance criteria
  - Tool/resource/prompt contract surfaces defined
  - Packaging, test, and rollout gates documented

### Future Enhancements

- ⏳ UI deprecation warnings from catalog
- ⏳ Weekly catalog auto-sync workflow
- 📝 MCP Server Core implementation (see `developer/PRD-MCP-implemenation.md`)
- 📝 MCP Server Extended (RAG tools, prompt exposure, subscriptions)
- 📝 MCP Client (deferred — tool orchestration loop)

See **developer/TODO.md** for detailed task breakdowns per phase.

## Documentation

### Core Documentation
- **README.md** — Project overview, quick start, usage examples
- **ENTERPRISE_README.md** — Enterprise deployment and features
- **docs/GETTING-STARTED.md** — Step-by-step onboarding guide
- **docs/API-REFERENCE.md** — Full API reference
- **docs/cli-usage.md** — CLI command reference (all 8 commands)
- **docs/PROMPT-TEMPLATES.md** — Prompt template system guide
- **docs/PROFILE-SYSTEM.md** — Profile system user guide
- **docs/PROFILE-SYSTEM-PLAN.md** — Profile system engineering plan
- **docs/StratifyAI-Router-Logic.md** — Router strategies, fallback chains, complexity analysis
- **docs/CATALOG_MANAGEMENT.md** — Community catalog contribution guide
- **docs/UI-OVERVIEW.md** — Svelte 5 SPA features and architecture
- **docs/StratifyAI-Prompt-Caching.md** — Prompt caching strategies
- **docs/large-file-strategies.md** — Large file handling approach
- **docs/performance.md** — Performance targets and benchmarks
- **developer/developer-journal.md** — Implementation log and lessons learned
- **docs/CHANGELOG.md** — Version history
- **docs/CONTRIBUTING.md** — Contribution guidelines
- **docs/project-status.md** — Current phase, milestones, and next steps
- **developer/TODO.md** — Prioritized roadmap (Phases 10–15)
- **developer/PRD-MCP-implemenation.md** — MCP technical approach and implementation phases
- **AGENTS.md** — This file (AI agent guidance)

## Troubleshooting

### Common Issues

**Virtual Environment Not Found:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Dependency Issues:**
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**Frontend Build Issues:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run build
```

**AWS Bedrock Auth Error:**
```bash
# Verify credentials are configured
aws sts get-caller-identity
# Ensure bedrock:InvokeModel permission is attached to your IAM user/role
```

## Development Best Practices

### Code Style
- Follow PEP 8 for Python code
- Use type hints on all public functions and methods
- Write Google-style docstrings for all public classes and methods
- Keep functions focused and single-purpose
- Ruff formatting/linting (line length 88) and Mypy type checking

### Type Safety & Mypy Configuration

**Mypy is configured in pyproject.toml with the following settings:**
- `python_version = "3.10"` - Target Python 3.10+ compatibility
- `check_untyped_defs = true` - Check definitions of untyped functions
- `no_implicit_optional = true` - Disallow implicit `Optional` types (PEP 484)
- `ignore_missing_imports = true` - Ignore missing stubs for external libraries

**Type Hint Patterns:**

1. **Required vs Optional Parameters:**
   ```python
   # ✅ Good: Optional parameters use `| None` syntax (PEP 604)
   def __init__(self, api_key: str, config: dict | None = None):
       pass

   # ❌ Bad: Implicit Optional (will fail mypy)
   def __init__(self, api_key: str, config: dict = None):
       pass
   ```

2. **Dictionary Type Inference:**
   ```python
   # ✅ Good: Cast values from .get() calls to ensure proper typing
   cost_input = float(model_info.get("cost_input", 0.0))
   return bool(model_info.get("supports_caching", False))

   # ❌ Bad: Returns `Any` from dict.get() without casting
   cost_input = model_info.get("cost_input", 0.0)  # Type: Any
   return model_info.get("supports_caching", False)  # Returns Any, not bool
   ```

3. **Indexed Dictionary Access:**
   ```python
   # ✅ Good: Use local variable with type guard
   inference_config = body["inferenceConfig"]
   if isinstance(inference_config, dict):
       inference_config["stopSequences"] = request.stop

   # ❌ Bad: Direct chained indexing may cause "Unsupported target" error
   body["inferenceConfig"]["stopSequences"] = request.stop
   ```

4. **Return Type Consistency:**
   ```python
   # ✅ Good: Explicitly cast arithmetic results to return type
   def _calculate_cost(self) -> float:
       input_cost = (tokens / 1_000_000) * cost_value  # Type: Any
       return float(input_cost)  # Explicit cast to float

   # ❌ Bad: Returns Any instead of declared float
   return input_cost + output_cost  # Type: Any, declared: float
   ```

**Running Mypy:**
```bash
# Check specific files
uv run mypy stratifyai/providers/openai.py

# Check specific directories
uv run mypy stratifyai

# Check with verbose output
uv run mypy --show-error-codes stratifyai
```

### Git Practices
- Never commit `.env` files or credentials
- Use `.gitignore` for environment files
- Write descriptive commit messages following the convention below
- Include co-author line: `Co-Authored-By: Oz <oz-agent@warp.dev>`

## Git Commit Convention

Use conventional commit format: `type(scope): brief description`

### Commit Types
- **feat**: New feature or functionality
- **fix**: Bug fix
- **docs**: Documentation changes
- **refactor**: Code refactoring without functionality change
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, config, infrastructure)
- **perf**: Performance improvements
- **style**: Code style/formatting changes

### Project Scopes
- **core**: Core functionality
- **api**: API endpoints
- **ui**: User interface
- **data**: Data processing
- **docs**: Documentation
- **tests**: Testing
- **config**: Configuration

### Guidelines
- Keep first line under 72 characters
- Use imperative mood ("add" not "added")
- Always include: `Co-Authored-By: Oz <oz-agent@warp.dev>`
- Scope is optional but recommended
- Reference issues when applicable: `fix(api): resolve connection issue (#123)`

### Example Commits
```
feat(core): add reasoning model temperature auto-disable
fix(ui): resolve WebSocket reconnection on model switch
docs(catalog): update Anthropic model deprecation dates
chore(deps): update openai SDK to 1.15.0
```

## Technical Constraints

### Must Maintain
- Python 3.10+ compatibility
- Type hints on all functions and methods
- Consistent BaseProvider interface across all providers
- Cost tracking accuracy to $0.0001
- Response time < 2 seconds (p95)
- Test coverage > 80%

### Security Requirements
- Never commit secrets or credentials
- Use environment variables for API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`, `GROK_API_KEY`, `OPENROUTER_API_KEY`)
- Protect API server endpoints with `STRATIFYAI_API_KEY` (Bearer token) in non-dev environments
- Validate all inputs to prevent injection attacks
- Sanitize error messages to avoid leaking API keys
- Apply DOMPurify XSS protection in frontend (already implemented)
- Implement rate limiting and budget enforcement

### Performance Targets
- Response time < 2 seconds (p95) for non-streaming requests
- Cold start < 1 second for provider initialization
- Memory usage < 100MB for client instance
- Cache hit rate > 30% with caching decorator enabled
- Cost reduction > 40% with cost-optimized routing

### Code Quality Standards
- Ruff formatting compliance (line length 88)
- Ruff linting compliance (all rules enabled)
- Mypy type checking passes with strict mode
- Docstrings on all public classes and methods (Google style)
- Unit test coverage > 80%
- Integration test coverage for all providers
