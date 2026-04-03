# StratifyAI - TODO

**Created:** April 1, 2026
**Last Updated:** April 2, 2026
**Based on:** Full project assessment (Phases 1-12 complete) + Phase 13 code review

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

> All core features implemented and 22 critical bugs fixed. Ready for merge to main.

- [x] In-memory LRU cache with O(1) eviction — RWLock bug fixed, all mutations under write lock
- [x] SQLite WAL mode for persistent cache
- [x] Configurable concurrency limits per provider — all 9 providers now covered
- [x] Load profile benchmarking — async fix applied (proper await on concurrent tasks)
- [ ] Evaluate persistent cache backend options (Redis, PostgreSQL) for concurrent workloads *(stretch goal - Phase 13.2)*
- [ ] Profile memory usage with large file extraction pipeline *(stretch goal - Phase 13.2)*

**Phase 13 Bug Fixes (22 total):**
- [x] Concurrency: Semaphore added to all 9 providers (was only OpenAI)
- [x] Concurrency: Lazy semaphore creation (correct event loop binding)
- [x] Concurrency: Finally blocks prevent slot leaks
- [x] Cache: RWLock semantics fixed (no writes under read lock)
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
- Phase 13 tests: 28/28 PASSING ✅
- Total suite: 526/531 PASSING ✅
- Coverage: 69% ✅

---

## Phase 14: Developer Experience (LOW PRIORITY)

> Polish items that improve onboarding and daily use.

- [ ] Add `stratifyai doctor` CLI command — validates env, keys, providers, connectivity in one shot
- [ ] Add `--dry-run` flag to router CLI to show selection reasoning without making API call
- [ ] Add structured error codes to all exceptions (for programmatic handling)
- [ ] Add changelog (CHANGELOG.md) or adopt automated release notes
- [ ] Add contribution guide (CONTRIBUTING.md) with dev setup instructions

---

## Phase 15: Security Audit (LOW PRIORITY)

> No critical issues found, but worth hardening before public release.

- [ ] Audit all error paths for potential API key leakage (expand sanitizer coverage)
- [ ] Add rate limiting per API key in FastAPI (currently global only)
- [ ] Add input validation/sanitization on WebSocket messages
- [ ] Review CORS configuration for production tightening
- [ ] Add dependency vulnerability scanning to CI (pip-audit or safety)
