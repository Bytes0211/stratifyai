# StratifyAI — Project Analysis

**Date:** February 10, 2026  
**Version Reviewed:** 0.1.3 (Phase 7.9)  
**Author:** Steven Cotton

---

## Executive Summary

StratifyAI is a well-architected Python framework providing a unified interface to 9 LLM providers (OpenAI, Anthropic, Google, DeepSeek, Groq, Grok, OpenRouter, Ollama, AWS Bedrock). The project demonstrates strong software engineering fundamentals — clean abstractions, good separation of concerns, comprehensive testing (300+ tests), and a thoughtful feature set including intelligent routing, cost tracking, caching, streaming, RAG, and a builder pattern API. It's a serious tool aimed at eliminating vendor lock-in for LLM-powered applications.

**Overall Assessment: Strong foundation with clear product vision. Ready for beta users with a handful of refinements.**

---

## Architecture & Design

### Strengths

**Clean Provider Abstraction** — The `BaseProvider` → `OpenAICompatibleProvider` → concrete provider hierarchy is the right call. Having 6 out of 9 providers inherit from `OpenAICompatibleProvider` reduces code duplication massively while still allowing Anthropic and Bedrock to use their native SDKs where the APIs diverge.

**Multiple API Surfaces** — The project exposes three well-layered interfaces, each serving a different user sophistication level:

1. **`LLMClient`** — full-control, explicit provider/model selection
2. **`chat` package** — simplified `anthropic.chat("Hello", model=...)` style
3. **`ChatBuilder`** — fluent builder pattern for reusable configurations

This is excellent API design — users can start simple and graduate to more power as needed.

**Immutable Builder Pattern** — `ChatBuilder._clone()` returns new instances on each `with_*` call. This avoids mutation bugs and allows safe reuse of partially-configured builders.

**Unified Data Models** — `ChatRequest`, `ChatResponse`, `Message`, and `Usage` dataclasses provide a single vocabulary across all 9 providers. Cost, latency, and token usage are normalized consistently.

### Areas for Improvement

**Dataclasses vs. Pydantic** — The models module uses `@dataclass` while the project already depends on `pydantic>=2.0.0`. Using Pydantic `BaseModel` for `ChatRequest`, `ChatResponse`, `Message`, and `Usage` would give you automatic validation, serialization, and better integration with FastAPI (which you're already using in the API layer). This is probably the single highest-ROI refactor.

**Config Module Size** — `config.py` is massive (~800+ lines of hardcoded dictionaries). While the `catalog_manager.py` exists for Anthropic models (loaded from `catalog/models.json`), all other providers are still inline. Migrating everything to the JSON catalog would make the project much more maintainable and enable community contributions without touching Python code.

**Sync Wrappers Use `asyncio.run()`** — Both `LLMClient.chat_sync()` and `ChatBuilder.chat_sync()` call `asyncio.run()`, which creates a new event loop each time. This will fail if called from within an existing async context (e.g., a FastAPI endpoint or Jupyter notebook). Consider using `asyncio.get_event_loop().run_until_complete()` with a fallback, or recommend `nest_asyncio` for notebook environments.

---

## Provider Coverage & Model Catalog

The 9-provider coverage is comprehensive and well-chosen. Notable details:

| Provider | Implementation | SDK | Models |
|---|---|---|---|
| OpenAI | Native | `openai` (async) | 14+ models incl. o-series reasoning |
| Anthropic | Native | `anthropic` (async) | Catalog-driven (JSON) |
| Google | OpenAI-compatible | `openai` with custom base URL | 3 Gemini 2.5 models |
| DeepSeek | OpenAI-compatible | Same | chat + reasoner |
| Groq | OpenAI-compatible | Same | Llama, Mixtral, GPT-OSS |
| Grok (X.AI) | OpenAI-compatible | Same | 12+ models incl. 2M context |
| OpenRouter | OpenAI-compatible | Same | 40+ models, free tier models |
| Ollama | OpenAI-compatible | Same | Local models |
| Bedrock | Native | `aioboto3`/`boto3` | Claude, Llama, Nova, Cohere, Mistral |

**Observations:**

- The OpenRouter catalog is particularly well-curated with free-tier models clearly marked — great for cost-conscious routing.
- The "future models" placeholders (GPT-5, GPT-5-mini, etc.) in the OpenAI catalog are forward-thinking but should be clearly labeled as speculative to avoid confusion.
- Grok's 2M token context window models are well-represented, which is a differentiator.
- The `INTERACTIVE_*_MODELS` dictionaries are a nice touch for CLI/UI model selection — curated subsets with display names and descriptions.

**Recommendation:** Finish migrating all providers to the JSON catalog system that Anthropic already uses. This is partially done; completing it would make model updates a data-only change.

---

## Intelligent Routing

The `Router` class implements four strategies — cost, quality, latency, and hybrid — with a well-designed complexity analyzer. The hybrid strategy dynamically adjusts weights based on task complexity, which is a smart approach.

**What works well:**
- The `_analyze_complexity()` method uses regex-based heuristics across 5 dimensions (reasoning keywords, length, code content, conversation depth, math content) — pragmatic and effective.
- `get_fallback_chain()` provides resilient routing with ranked alternatives.
- `route_for_extraction()` has task-specific weighting for file extraction scenarios.
- Capability filtering (vision, tools, reasoning) constrains the candidate pool intelligently.

**What could be improved:**
- Quality scores and latency estimates are hardcoded. Adding telemetry to track actual latency per model and adjusting scores dynamically would make routing significantly smarter over time.
- The complexity analyzer doesn't account for multi-modal content (images). A message with vision content should strongly prefer vision-capable models even in hybrid mode.
- Cost normalization in `_select_hybrid()` uses a fixed $0.050/1k ceiling. With models ranging from free to $60/1M output, this could be recalibrated.

---

## Caching

The `ResponseCache` is a clean, thread-safe in-memory LRU cache with TTL expiration and cost-savings tracking. The `@cache_response` decorator and `generate_cache_key()` function make it easy to add caching to any async function.

**Strengths:** Thread-safe with `threading.Lock`, tracks hit rates and cost savings, configurable TTL and max size.

**Gaps:**
- In-memory only — no persistence across process restarts. For a "production-ready" framework, an optional Redis or SQLite backend would be valuable.
- The global singleton pattern (`_global_cache`) works but isn't configurable per-client. If a user wants different TTLs for different providers, they'd need to manage their own instances.
- No cache invalidation by model or provider — if a model's pricing changes or a response is known-bad, there's no way to selectively clear entries.

---

## RAG Pipeline

The RAG implementation is functional and well-structured: chunk → embed → store (ChromaDB) → query → generate with citations. The `RAGClient` cleanly composes `EmbeddingProvider`, `VectorDBClient`, and `LLMClient`.

**Strengths:**
- `index_file()` and `index_directory()` with configurable chunk size and overlap.
- The query method builds a citation-aware prompt template.
- `retrieve_only()` allows testing retrieval quality independently of generation.
- Collection management (list, delete, stats) is complete.

**Areas for improvement:**
- Only OpenAI embeddings are supported via `create_embedding_provider("openai")`. Adding Bedrock Titan, Google, or local embedding models would align with the multi-provider philosophy.
- The chunking strategy is character-based. For production RAG, token-based chunking with semantic boundary detection (paragraph, section) would improve retrieval quality.
- No re-ranking step between retrieval and generation — this is a common enhancement that significantly improves RAG output quality.

---

## Error Handling & Exceptions

The exception hierarchy is well-designed and granular:

```
LLMAbstractionError
├── ProviderError
│   ├── InvalidProviderError
│   ├── ProviderAPIError (includes provider name + status code)
│   ├── AuthenticationError
│   ├── InsufficientBalanceError
│   ├── RateLimitError (includes retry_after)
│   └── InvalidModelError
├── BudgetExceededError
├── MaxRetriesExceededError
└── ValidationError
```

Vision-related errors are caught and re-raised with helpful messages suggesting alternative models. The `OpenAICompatibleProvider` base class properly distinguishes between `APIStatusError`, `APIError`, and generic exceptions with specific handling for insufficient balance, auth failures, and vision errors.

**One gap:** `RateLimitError` captures `retry_after` but there's no automatic retry-with-backoff at the client level that uses this value. The `retry.py` module exists but isn't automatically integrated into the main request path.

---

## Testing

The project claims 300+ tests across 19 test files. The test structure covers:

- Core client logic (`test_client.py`, `test_models.py`)
- Individual providers (`test_openai_provider.py`, `test_bedrock_provider.py`)
- Router and routing strategies (`test_router.py`, `test_router_extraction.py`)
- Caching (`test_caching.py`, `test_phase74_caching.py`)
- Builder pattern (`test_chat_builder.py`)
- CLI (`test_cli_chat.py`, `test_cli_auth_error.py`, `test_cli_file_loading.py`)
- Temperature validation (`test_temperature_unit.py`, `test_temperature_validation.py`)

**Configuration:** `pytest.ini_options` in `pyproject.toml` is well-configured with `asyncio_mode = "auto"`, strict markers, and custom markers for slow/integration tests.

**Recommendations:**
- Add integration tests that hit real APIs (behind a marker/flag) to catch SDK version incompatibilities.
- Add property-based testing (hypothesis) for the router's scoring functions to catch edge cases in cost/quality normalization.
- The test file naming has some legacy patterns (`test_phase71.py`, `test_phase72_extractors.py`) — renaming to feature-based names would improve discoverability.

---

## Project Health & DevOps

**Tooling:** The project uses a modern Python stack — `uv` for package management, `ruff` for formatting/linting, `mypy` for type checking, and `pytest` for testing. All configured in `pyproject.toml`.

**Packaging:** Proper `setup.py` + `pyproject.toml` with optional dependency groups (`dev`, `cli`, `web`, `rag`, `all`). The `stratifyai` CLI entrypoint is registered. A `py.typed` marker is included for PEP 561 compliance.

**Documentation:** Extensive — 18 docs files covering API reference, getting started, CLI usage, contributing guidelines, router logic, prompt caching, stakeholder presentation, and even a competitive comparison (LangChain vs StratifyAI vs LiteLLM).

**Version inconsistency:** `__init__.py` says `0.1.0`, `pyproject.toml` says `0.1.3`. These should be synced, ideally via a single source of truth (e.g., `importlib.metadata`).

---

## Key Recommendations (Priority Ordered)

1. **Migrate models to Pydantic** — Replace dataclasses with Pydantic BaseModel for ChatRequest/ChatResponse/Message/Usage. Biggest quality-of-life improvement for validation, serialization, and FastAPI integration.

2. **Complete the JSON catalog migration** — Move all provider model metadata from `config.py` into `catalog/models.json`. This makes model updates a data-only PR and unblocks community contributions.

3. **Fix sync wrappers** — Replace `asyncio.run()` with a more robust pattern that works inside existing event loops. This is a common pain point for users in notebooks and web frameworks.

4. **Add dynamic routing telemetry** — Track actual latency and success rates per model/provider. Use this data to refine quality scores and latency estimates over time instead of relying on hardcoded values.

5. **Expand embedding providers** — Add at least one non-OpenAI embedding provider (e.g., local sentence-transformers via Ollama) to match the multi-provider ethos.

6. **Sync version numbers** — Establish a single source of truth for the package version.

7. **Add persistent cache option** — Even a simple SQLite backend would make the caching story much more compelling for production use.

8. **Integrate retry logic into the main request path** — The `RetryConfig` and `with_retry` exist in `retry.py` but aren't automatically applied by `LLMClient`. Wire them up with the `RateLimitError.retry_after` value.

---

## Summary Scorecard

| Dimension | Rating | Notes |
|---|---|---|
| Architecture | ⭐⭐⭐⭐⭐ | Clean abstractions, good layering, extensible |
| Code Quality | ⭐⭐⭐⭐ | Well-typed, consistent patterns, thorough docstrings |
| Feature Completeness | ⭐⭐⭐⭐ | Routing, caching, RAG, streaming, vision — comprehensive |
| Testing | ⭐⭐⭐⭐ | 300+ tests, good coverage, could add integration tests |
| Documentation | ⭐⭐⭐⭐⭐ | Exceptional — API docs, guides, stakeholder materials |
| Production Readiness | ⭐⭐⭐½ | Strong beta; needs persistent caching, retry integration |
| DX (Developer Experience) | ⭐⭐⭐⭐⭐ | Builder pattern, auto-detection, helpful error messages |

**Bottom line:** StratifyAI is an impressive single-developer project with the architecture and feature depth of something built by a team. The multi-layered API surface (client → chat → builder), intelligent routing, and 9-provider coverage position it well as a serious LiteLLM/LangChain alternative with a cleaner, more Pythonic API. The recommendations above are refinements, not overhauls — the foundation is solid.
