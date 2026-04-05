# Code Review Action Plan

**Review Date:** April 4, 2026
**Scope:** Full codebase review — architecture, code quality, security, testing, documentation
**Status:** Phase R1 Complete — R2/R3 Planned

---

## Phase R1: Critical Fixes (This Sprint)

> ✅ Completed on April 4, 2026 — provider/cache locking, websocket synchronization, explicit stream cleanup, request validation hardening, and doc corrections were implemented and verified.

Focuses on concurrency bugs, resource leaks, and security gaps that affect correctness under load.

| Step | Area | Description | Files | Status |
|------|------|-------------|-------|--------|
| R1.1 | Concurrency | Add `threading.Lock` to `_provider_pool` dict to prevent race conditions (GIL-dependent today, breaks under Python 3.13+ free-threading) | `stratifyai/client.py:52-77` | ✅ Complete |
| R1.2 | Concurrency | Add `asyncio.Lock` to `_client_cache` and `_mcp_chat_engine` initialization to prevent duplicate instances | `api/main.py:102-125` | ✅ Complete |
| R1.3 | Concurrency | Add synchronization to `_ws_rate_limit` dict to prevent iteration errors under concurrent WebSocket connections | `api/main.py:301-331` | ✅ Complete |
| R1.4 | Resource Leak | Fix streaming generator cleanup — explicitly `aclose()` async generators on retry/exception to prevent semaphore slot leaks | `stratifyai/client.py:474`, `stratifyai/providers/base.py:71-87` | ✅ Complete |
| R1.5 | Security | Add parameter validation to MCP tools — range checks on `temperature` (0.0–2.0), `max_tokens` (1–4M), non-empty `messages` | `stratifyai/mcp_server/tools.py:109-212` | ✅ Complete |
| R1.6 | Security | Add Pydantic field validators to `ChatCompletionRequest` for `provider`, `temperature`, `max_tokens` | `api/main.py` (ChatCompletionRequest model) | ✅ Complete |
| R1.7 | Docs | Fix `STRATUMAI_PROVIDER` / `STRATUMAI_MODEL` typos — replace with correct env var references or remove | `docs/cli-usage.md`, `docs/quick-start-guide.md`, `examples/cli_interactive_demo.md` | ✅ Complete |
| R1.8 | Code + Docs | Eliminate hardcoded model names from runtime code, docs, and examples. Models change frequently — hardcoded names rot and break. Code should resolve defaults from `catalog/models.json`; docs should use placeholders or `stratifyai list-models` references. See Appendix A for full inventory (code and docs). | See Appendix A | 🟡 In Progress |

---

## Phase R2: Hardening & Test Coverage (1–2 Sprints)

Addresses code organization, test gaps, and security improvements that reduce risk over time.

| Step | Area | Description | Files | Status |
|------|------|-------------|-------|--------|
| R2.1 | Code Org | Refactor `cli/stratifyai_cli.py` (154KB) into submodules — split by command group (chat, mcp, file, route, cache) | `cli/stratifyai_cli.py` → `cli/commands/*.py` | ⬜ Not Started |
| R2.2 | Code Org | Refactor `api/main.py` (102KB) into FastAPI routers — separate chat, catalog, health, MCP, metrics endpoints | `api/main.py` → `api/routers/*.py` | ⬜ Not Started |
| R2.3 | Testing | Add dedicated tests for `summarization.py` (currently 16% coverage) — target 80% | `tests/test_summarization.py` (new) | ⬜ Not Started |
| R2.4 | Testing | Add end-to-end RAG pipeline test (document → chunks → embeddings → vector DB → retrieval) — currently 35% coverage | `tests/test_rag_integration.py` (new) | ⬜ Not Started |
| R2.5 | Testing | Add API endpoint tests using FastAPI `TestClient` — cover all 40+ REST endpoints and WebSocket streaming | `tests/test_api_endpoints.py` (new) | ⬜ Not Started |
| R2.6 | Testing | Replace `time.sleep()` assertions in caching tests with `freezegun` to eliminate flaky time-based tests | `tests/test_caching.py`, `tests/test_persistent_cache.py` | ⬜ Not Started |
| R2.7 | Testing | Raise coverage threshold from 65% → 75% | `pyproject.toml` ([tool.pytest]), `.github/workflows/ci.yml` | ⬜ Not Started |
| R2.8 | Security | Protect or minimize health endpoint info disclosure — remove version from `/api/health`, restrict `/health/providers` | `api/main.py:2771, 2856-2857` | ⬜ Not Started |
| R2.9 | Security | Move WebSocket authentication before `websocket.accept()` — validate auth, then accept connection | `api/main.py:1037-1060` | ⬜ Not Started |
| R2.10 | Security | Pass `api_key` parameter to `sanitize_error()` in retry logging to ensure all key formats are redacted | `stratifyai/retry.py:113` | ⬜ Not Started |
| R2.11 | Bug Fix | Fix Anthropic cache token math — use `max(0, prompt_tokens - cache_read_tokens)` to prevent negative costs | `stratifyai/providers/anthropic.py:312` | ⬜ Not Started |
| R2.12 | Bug Fix | Include `extra_params` in cache key generation to prevent cache collisions | `stratifyai/caching.py:509-519` | ⬜ Not Started |

---

## Phase R3: Polish & Long-Term Quality (Next Quarter)

Addresses design improvements, documentation consolidation, and forward-looking hardening.

| Step | Area | Description | Files | Status |
|------|------|-------------|-------|--------|
| R3.1 | Code Quality | Extract reasoning model detection to shared method — eliminate duplication between `chat_completion()` and `chat_completion_stream()` | `stratifyai/providers/openai.py:133-152, 248-264` | ⬜ Not Started |
| R3.2 | Code Quality | Add response validation in provider normalize functions — check for empty `choices`, missing `content` fields | `stratifyai/providers/openai.py:312`, `stratifyai/providers/anthropic.py:299` | ⬜ Not Started |
| R3.3 | Security | Add file size limits before API file processing — prevent OOM/DoS from oversized uploads | `api/main.py:787-860, 1101-1276` | ⬜ Not Started |
| R3.4 | Security | Add memory bounds or LRU cleanup to global `CostTracker` — prevent unbounded growth in long-running servers | `api/main.py:293`, `stratifyai/mcp_server/tools.py:31-32` | ⬜ Not Started |
| R3.5 | API Design | Add API versioning (`/v1/` prefix) to REST endpoints for stability across releases | `api/main.py` (all route definitions) | ⬜ Not Started |
| R3.6 | Docs | Consolidate getting-started documentation — merge README, GETTING-STARTED, quick-start-guide, local-installation-guide into single flow | `docs/GETTING-STARTED.md`, `docs/quick-start-guide.md`, `docs/local-installation-guide.md` | ⬜ Not Started |
| R3.7 | Docs | Add `examples/README.md` with quick reference and recommended learning order for each example | `examples/README.md` (new) | ⬜ Not Started |
| R3.8 | Docs | Document Vision support with usage examples — feature exists in providers but has no user-facing guide | `docs/` (new or extend API-REFERENCE.md) | ⬜ Not Started |
| R3.9 | Docs | Update test count badges — README (536 → 669), ENTERPRISE_README (300+ → 669) | `README.md:6`, `ENTERPRISE_README.md:5` | ⬜ Not Started |
| R3.10 | Testing | Add tests for `bedrock_validator.py` (0% coverage) and `provider_validator.py` (0% coverage) | `tests/test_bedrock_validator.py` (new), `tests/test_provider_validator.py` (new) | ⬜ Not Started |
| R3.11 | Testing | Raise coverage threshold from 75% → 85% after R2 test additions stabilize | `pyproject.toml`, `.github/workflows/ci.yml` | ⬜ Not Started |
| R3.12 | Config | Make `ThreadPoolExecutor` max_workers configurable via env var (currently hardcoded to 4) | `api/main.py:98-99` | ⬜ Not Started |

---

## Appendix A: Hardcoded Model Names Inventory (R1.8)

Model names are hardcoded across **runtime code**, docs, and examples. When models are deprecated or renamed, these references break silently. The catalog (`catalog/models.json`) is the source of truth — code should resolve defaults from it, not from inline strings.

### Part 1: Hardcoded models in RUNTIME CODE (highest priority)

These are in code paths that execute at runtime — not docstrings or comments.

#### Default function parameters

| File | Lines | Hardcoded Model | Context |
|------|-------|-----------------|---------|
| `stratifyai/summarization.py` | 19, 68, 145, 192, 244, 285 | `gpt-4o-mini` | Default `model` param on 6 functions |
| `stratifyai/rag.py` | 228 | `gpt-4o-mini` | Default `model` param on `query()` |
| `stratifyai/utils/file_analyzer.py` | 123 | `gpt-4o` | Default `model` param on `analyze_file()` |
| `cli/stratifyai_cli.py` | 1268 | `gpt-4o` | Fallback when no model specified |

#### Hardcoded model lookup tables (duplicates catalog data)

| File | Lines | Issue |
|------|-------|-------|
| `stratifyai/utils/model_selector.py` | 47-74 | 4 hardcoded model lists for extraction modes (schema, error, code, summary) — includes non-existent `gpt-4.1-mini` |
| `stratifyai/utils/model_selector.py` | 248-276 | Hardcoded `quality_scores` dict (24 models) — duplicates `catalog/models.json` quality_score field |
| `stratifyai/utils/model_selector.py` | 289-302 | Hardcoded `cost_estimates` dict (12 models) — duplicates catalog cost fields. Comment says "should match MODEL_CATALOG" |
| `stratifyai/config.py` | 94-170 | `INTERACTIVE_*_MODELS` dicts — curated subsets, but model names are inline strings |
| `stratifyai/config.py` | 248-300 | `OPENROUTER_MODELS` fallback dict with hardcoded model names |

#### Hardcoded summarization model maps (duplicated twice)

| File | Lines | Issue |
|------|-------|-------|
| `api/main.py` | 829-841 | Provider-to-summarization-model dict (9 providers) — REST path |
| `api/main.py` | 1221-1233 | **Exact duplicate** of the above — WebSocket path |

#### Hardcoded model names in error messages and suggestions

| File | Lines | Model | Context |
|------|-------|-------|---------|
| `stratifyai/providers/openai.py` | 192, 289 | `gpt-4o`, `gpt-4o-mini` | Vision error message suggestion |
| `stratifyai/providers/anthropic.py` | 183, 275 | `claude-sonnet-4-5`, `claude-opus-4-5` | Vision error message suggestion |
| `stratifyai/providers/openai_compatible.py` | 195 | `gemini-2.5-pro`, `gpt-4o` | Vision error message suggestion |
| `api/main.py` | 541-543, 1007 | `gemini-2.5-pro`, `gemini-2.5-flash` | Token limit suggestion messages |
| `api/main.py` | 1715, 1780, 1822 | `gpt-4o-mini` | API docs/example payloads |

### Part 2: Hardcoded models in DOCSTRINGS and COMMENTS (lower priority)

These don't affect runtime but will mislead developers reading the code.

| File | Lines | Issue |
|------|-------|-------|
| `stratifyai/chat/stratifyai_openai.py` | 13, 18, 103, 115, 153, 164, 213 | 7 refs to `gpt-4.1-mini` / `gpt-4.1` — **non-existent models** |
| `stratifyai/chat/__init__.py` | 9, 24 | `gpt-4.1-mini`, `claude-sonnet-4-5` in module docstring |
| `stratifyai/chat/builder.py` | 9, 89, 200 | `claude-sonnet-4-5`, `gpt-4.1` in docstrings |
| `stratifyai/chat/stratifyai_anthropic.py` | 13, 103, 115, 153, 164 | `claude-sonnet-4-5` in docstrings |
| `stratifyai/chat/stratifyai_google.py` | 13, 18, 103, 115, 153, 164 | `gemini-2.5-flash`, `gemini-2.5-pro` in docstrings |
| `stratifyai/client.py` | 324 | `gpt-4.1-mini` in docstring — **non-existent** |
| `stratifyai/mcp_server/prompts.py` | 25 | `gpt-4.1` in prompt description — **non-existent** |
| `stratifyai/router.py` | 476 | `gpt-4o`, `claude-3-5-sonnet` in docstring example |

### Part 3: Hardcoded models in DOCS and EXAMPLES

| File | Occurrences | Severity |
|------|-------------|----------|
| `api/README.md` | 2 | `gpt-4.1-mini` — **non-existent** |
| `docs/MCP-QUICKSTART.md` | 2 | `gpt-4.1`, `gpt-4.1-mini` — **non-existent** |
| `docs/API-REFERENCE.md` | 4+ | `gpt-4.1-mini` — **non-existent** |
| `examples/caching_examples.py` | 8 | `gpt-4.1-mini` — **non-existent** |
| `examples/chatbot.py` | 4 | `gpt-4.1`, `gpt-4.1-mini` — **non-existent** |
| `examples/code_reviewer.py` | 1 | `gpt-4.1` — **non-existent** |
| `README.md` | 6 | `gpt-4o-mini`, `claude-sonnet-4-5` — valid but fragile |
| `ENTERPRISE_README.md` | 4 | `gpt-4o-mini`, `claude-sonnet-4-5` — valid but fragile |
| `docs/local-installation-guide.md` | 8+ | Various — valid but fragile |
| `examples/web_server.py` | 5 | Various — valid but fragile |
| `examples/performance_benchmark.py` | 5 | `gpt-4o-mini` defaults — valid but fragile |

### Recommended approach

**Runtime code (Part 1):**

1. **Default model params**: Replace hardcoded defaults with a catalog lookup helper (e.g., `get_default_model(provider, category="cheap")`) that resolves from `catalog/models.json`
2. **model_selector.py quality/cost dicts**: Read scores and costs from `MODEL_CATALOG` instead of duplicating them inline — the comment on line 288 already says "should match MODEL_CATALOG"
3. **Summarization model maps in api/main.py**: Extract to a shared constant or catalog lookup — the two copies (lines 829 and 1221) are identical and will drift
4. **Error message suggestions**: Acceptable as-is since they're human-readable hints, but consider referencing vision-capable models generically where possible

**Docs and examples (Parts 2-3):**

1. **Docstrings**: Use generic forms like `"your-model"` or reference categories ("a vision-capable model") instead of specific model IDs
2. **Examples**: Define a `MODEL` constant at the top of each file with a comment: `# Update from catalog/models.json or run: stratifyai list-models`
3. **README/ENTERPRISE_README**: Keep a small number of examples but add a note that model names change — link to catalog
4. **Non-existent models**: Remove all `gpt-4.1` / `gpt-4.1-mini` references immediately — these have never existed

**Skip**: `catalog/models.json` (the catalog itself), `catalog/README.md` (reference docs), `AGENTS.md` Bedrock list (provider reference), test files (mocking), `config.py` INTERACTIVE dicts (curated UI lists — acceptable if kept in sync with catalog)
