# StratifyAI - TODO

**Created:** April 1, 2026
**Last Updated:** April 2, 2026
**Based on:** Full project assessment (Phases 1-15 complete) + PR review fixes

---

## Phase 13 Bug Fixes (CRITICAL — blocks merge)

> Phase 13 code review uncovered critical bugs in the cache, concurrency, and streaming
> implementations. These must be resolved before the `chore/performance-scalability` branch
> can be merged.

### Concurrency — providers

- [x] Add `_acquire/_release_concurrency_slot()` to `AnthropicProvider.chat_completion()` and `chat_completion_stream()`
- [x] Add `_acquire/_release_concurrency_slot()` to `OpenAICompatibleProvider.chat_completion()` and `chat_completion_stream()` (covers Groq, DeepSeek, Grok, Google, OpenRouter, Ollama)
- [x] Add `_acquire/_release_concurrency_slot()` to `BedrockProvider.chat_completion()` and `chat_completion_stream()`
- [x] Fix race condition in `BaseProvider.set_concurrency_limit()` — semaphore now created lazily, old semaphore no longer replaced mid-flight
- [x] Create `asyncio.Semaphore` lazily on first async use, not eagerly in sync `set_concurrency_limit()` — avoids wrong-event-loop binding

### Cache — `stratifyai/caching.py`

- [x] Move write operations (`entry.hits`, `entry.cost_saved`, `self._total_cost_saved`) out of read lock in `ResponseCache.get()` — all mutations now under write lock only
- [x] Fix `NameError` in `cache_response()` decorator when `args` is empty or `args[0]` has no `model` attribute — renamed to `request_obj` with proper None check
- [x] Fix double-counting of `_total_misses` (single increment path now)
- [x] Guard against `cost_usd` being `None` before adding to float in `ResponseCache.get()`

### Client — `stratifyai/client.py`

- [x] Add catch-all `except Exception` with re-raise in `_stream_with_retry()` — non-retryable exceptions now propagate immediately
- [x] Replace `str(hash(api_key))[:12]` in `_pool_key()` with `hashlib.sha256` — stable across processes

### Benchmark — `examples/performance_benchmark.py`

- [x] Fix concurrent load profiles — `client.chat()` was missing `await`, so coroutines were never executed. Now properly awaited for true concurrent benchmarking

### Tests — new test files

- [x] Remove `except Exception: pass` patterns across all three test files — exceptions now propagate
- [x] Replace wall-clock timing assertions with generous thresholds (5s/1s/5s)
- [x] Fix race condition in `MockProvider.max_concurrent_observed` tracking — added `asyncio.Lock` around counter updates
- [x] Add data correctness validation in `test_caching_concurrency.py` — reads now verify model/content/provider fields; new `TestCacheDataCorrectness` class verifies distinct values survive concurrent writes
- [x] Fix FIFO order test in `test_provider_concurrency.py` — renamed to `test_sequential_queueing_behavior`, asserts `max_concurrent_observed == 1` and all task IDs complete
- [x] Replace `time.sleep()` TTL test with generous thresholds (2.5s margin)

### Integration test flake

- [x] Root cause identified: Google API key IP restriction, not event loop issue. Lazy semaphore creation resolved the theoretical event loop binding concern. Test correctly skips when no API keys are set.

---

## Completed Phases

<details>
<summary>Phase 10: CI/CD & Testing Infrastructure ✅</summary>

- [x] Add GitHub Actions workflow to run full test suite on PR/push
- [x] Add linting step to CI (Ruff)
- [x] Add type checking step to CI (Mypy)
- [x] Add code formatting check to CI (Ruff format --check)
- [x] Add integration test suite with real provider calls (gated behind `integration` marker + secrets)
- [x] Remove committed frontend build artifacts from `api/static/dist/` — build in CI instead
- [x] Add test coverage reporting (pytest-cov) with minimum threshold

</details>

<details>
<summary>Phase 11: Error Handling & Validation Hardening ✅</summary>

- [x] Move API key validation to client initialization (fail-fast instead of on first request)
- [x] Add client-level temperature validation for reasoning models (o1, o3) before reaching provider
- [x] Apply retry logic consistently across all code paths (some paths skip `@retry`)
- [x] Add granular timeout configuration per provider (some providers are slower than others)
- [x] Add cancellation support for long-running async operations

</details>

<details>
<summary>Phase 12: Observability & Streaming ✅</summary>

- [x] Track full end-to-end latency for streaming responses (first token + total)
- [x] Add detailed logging for cache hits/misses (model, key, TTL remaining)
- [x] Add request/response tracing with correlation IDs
- [x] Add provider health check endpoint to API (`/health/providers`)
- [x] Add metrics export (Prometheus-compatible or structured JSON)

</details>

---

## Phase 13: Performance & Scalability (✅ COMPLETE)

> All core features implemented and 22+ critical bugs fixed. Ready for merge to main.

- [x] In-memory LRU cache with O(1) eviction — all operations under write lock (LRUCache mutates on read)
- [x] SQLite WAL mode for persistent cache
- [x] Configurable concurrency limits per provider — all 9 providers now covered
- [x] Load profile benchmarking — async fix applied (proper await on concurrent tasks)
- [ ] Evaluate persistent cache backend options (Redis, PostgreSQL) for concurrent workloads *(stretch goal - Phase 13.2)*
- [ ] Profile memory usage with large file extraction pipeline *(stretch goal - Phase 13.2)*

**Phase 13 Bug Fixes (22 total + PR review fixes):**
- [x] Concurrency: Semaphore added to all 9 providers (was only OpenAI)
- [x] Concurrency: Lazy semaphore creation (correct event loop binding)
- [x] Concurrency: Finally blocks prevent slot leaks
- [x] Concurrency: Semaphore ref captured locally to prevent deadlock on mid-flight limit change (PR #17)
- [x] Cache: LRUCache `get()` moved to write lock (LRUCache.__getitem__ mutates LRU order) (PR #17)
- [x] Cache: NameError in decorator fixed
- [x] Cache: Double-counted misses fixed
- [x] Cache: cost_usd None guarding
- [x] Client: Streaming retry catch-all
- [x] Client: SHA-256 pool key (stable)
- [x] Benchmark: Async simulation fixed
- [x] Tests: Exception swallowing removed
- [x] Tests: Generous timing thresholds
- [x] Tests: Race conditions fixed
- [x] Tests: Data correctness validation added

**Test Results:**
- Total suite: 536 PASSING, 4 skipped ✅
- Coverage: 69% ✅

---

## Phase 14: Developer Experience (LOW PRIORITY)

> Polish items that improve onboarding and daily use.

- [x] Add `stratifyai doctor` CLI command — validates env, keys, providers, connectivity in one shot
- [x] Add `--dry-run` flag to router CLI to show selection reasoning without making API call
- [x] Add structured error codes to all exceptions (for programmatic handling)
- [x] Add changelog (CHANGELOG.md) or adopt automated release notes
- [x] Add contribution guide (CONTRIBUTING.md) with dev setup instructions

---

## Phase 15: Security Audit (✅ COMPLETE)

> Hardened for public release. All gaps identified and fixed.

- [x] Audit all error paths for potential API key leakage (expand sanitizer coverage)
  - Fixed: `_initialize_client()` in all 4 providers now sanitizes errors
  - Fixed: `embeddings.py` error paths now use `sanitize_error()`
  - Fixed: `retry.py` log messages now sanitized
- [x] Add rate limiting per API key in FastAPI (currently global only)
- [x] Add input validation/sanitization on WebSocket messages
  - Fixed: Added provider/model validation against `MODEL_CATALOG`
  - Fixed: Added temperature bounds check (0.0–2.0)
  - Fixed: Removed redundant `auth_header` reassignment
- [x] Review CORS configuration for production tightening
- [x] Add dependency vulnerability scanning to CI (pip-audit)
  - Fixed: CI now scans full resolved dependency graph via `uv export --all-extras`
  - Fixed: All 6 vulnerable deps updated (aiohttp, requests, cryptography, protobuf, pyasn1, pygments)

---

## Open Follow-ups (from PRD Phase 8 audit)

> Remaining gaps validated against current codebase after Phase 15.

- [x] **P0 — WebSocket token-limit parity with REST path**
	- Extracted `_check_token_limits()` helper in `api/main.py`; called from both REST and WebSocket paths.
	- WebSocket translates `HTTPException` into `{error, detail, estimated_tokens, done:True}` JSON message.
	- 5 new tests in `tests/test_token_limit_and_ttl.py` covering all limit branches.

- [x] **P1 — Per-decorator TTL behavior for `cache_response`**
	- Added `ttl: int | None` field to `CacheEntry`; `ResponseCache.set()` / `PersistentResponseCache.set()` now accept and store per-entry TTL.
	- `get()` uses `entry.ttl` (or `self.ttl` fallback) for expiry; decorator forwards its `ttl` to both backends.
	- SQLite schema migration adds `ttl_override` column idempotently via guarded `ALTER TABLE`.
	- 12 new tests covering in-memory, SQLite, and decorator paths.

### Execution Order

1. P0 — WebSocket token-limit parity with REST path
2. P1 — Per-decorator TTL behavior for `cache_response`

---

## MCP Server (COMPLETE)

> MCP server exposing StratifyAI via standardized tool/resource/prompt primitives.
> Reference: `developer/PRD-MCP-implemenation.md` (v1.2), `developer/MCP-IMPLEMENTATION-PLAN.md`

- [x] Phase 0 — Contract Freeze (PRD + implementation plan)
- [x] Phase 1 — Server Bootstrap (FastMCP scaffold, `stratifyai-mcp` entrypoint, schemas, error mapping)
- [x] Phase 2 — Core Tools (`chat_completion`, `chat_with_routing`, `list_providers`, `list_models`, `get_model_info`)
- [x] Phase 3 — Cost & Validation Tools (`get_cost_summary`, `validate_provider`, `estimate_cost`)
- [x] Phase 4 — Resource Layer (`stratifyai://catalog`, `providers`, `costs`, `router/strategies`)
- [x] Phase 5 — Prompt Exposure (3 named prompts + dynamic registry template exposure)
- [x] Phase 7 — Tests & CI Gates (75 MCP tests, 71%+ coverage, CI updated)
- [x] Phase 8 — Docs & Client Setup (quickstart, tools reference, client config guides)
- [ ] Phase 6 — HTTP Transport (deferred, post-GA)
- [ ] Phase 9 — Rollout & Verification (deferred until Client Engine proves full stack)

**Test Results:** 632 passing, 4 skipped, 71%+ coverage

---

## MCP Abstraction Layer (IN PROGRESS)

> Catalog, config wizard, and inline tool tester for MCP server management.
> Reference: `developer/PRD-MCP-abstraction-layer.md`

- [ ] AL-1 — Catalog + CLI Core (catalog.json, `stratifyai mcp setup` wizard, config generation, prereq validation) **← CURRENT**
- [ ] AL-2 — Additional CLI Commands (`mcp status/add/add-custom/remove`, dry-run)
- [ ] AL-3 — Web UI (Svelte tab, browse/toggle/configure, context-aware Apply/Export)
- [ ] AL-4 — Inline Tool Tester (JSON editor, tool browser, presets, test API endpoint)
- [ ] AL-5 — Polish (health checks, custom server Web UI, tests and docs)

---

## MCP Client Engine (FUTURE)

> StratifyAI as MCP client — spawns and calls external MCP servers.
> Reference: `developer/PRD-MCP-client-engine.md`

- [ ] CE-1 — Client Engine Core (spawn servers, handshake, call_tool, get_resource)
- [ ] CE-2 — Tool Registry & Namespacing (aggregated tool list across servers)
- [ ] CE-3 — Chat Integration (LLM tool_use with MCP tools in conversation)
- [x] CE-4 — Permissions & Safety (allow/deny/confirm per tool, safety defaults)
- [x] CE-5 — Web UI Panels (server dashboard, tool discovery, chat badges, permission manager)
- [x] CE-6 — API & Diagnostics (REST endpoints, health monitoring)
- [ ] CE-7 — Tests & Documentation

**Execution order:** AL-1 → AL-2 → CE-1 → CE-2 → AL-3 → CE-3 → CE-4 → AL-4 → CE-5 → CE-6 → AL-5 + CE-7
See `developer/MCP-STATUS.md` for full rationale.
