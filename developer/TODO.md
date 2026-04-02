# StratifyAI - TODO

**Created:** April 1, 2026
**Based on:** Full project assessment (Phases 1-9 complete)

---

## Phase 10: CI/CD & Testing Infrastructure (HIGH PRIORITY)

> The biggest gap — no automated quality gates in CI beyond catalog validation.

- [x] Add GitHub Actions workflow to run full test suite on PR/push
- [x] Add linting step to CI (Ruff)
- [x] Add type checking step to CI (Mypy)
- [x] Add code formatting check to CI (Ruff format --check)
- [x] Add integration test suite with real provider calls (gated behind `integration` marker + secrets)
- [x] Remove committed frontend build artifacts from `api/static/dist/` — build in CI instead
- [x] Add test coverage reporting (pytest-cov) with minimum threshold

---

## Phase 11: Error Handling & Validation Hardening (HIGH PRIORITY)

> Late failures and inconsistent validation hurt developer experience.

- [x] Move API key validation to client initialization (fail-fast instead of on first request)
- [x] Add client-level temperature validation for reasoning models (o1, o3) before reaching provider
- [x] Apply retry logic consistently across all code paths (some paths skip `@retry`)
- [x] Add granular timeout configuration per provider (some providers are slower than others)
- [x] Add cancellation support for long-running async operations

---

## Phase 12: Observability & Streaming (MEDIUM PRIORITY)

> Gaps in latency tracking and logging for streamed responses.

- [ ] Track full end-to-end latency for streaming responses (first token + total)
- [ ] Add detailed logging for cache hits/misses (model, key, TTL remaining)
- [ ] Add request/response tracing with correlation IDs
- [ ] Add provider health check endpoint to API (`/health/providers`)
- [ ] Add metrics export (Prometheus-compatible or structured JSON)

---

## Phase 13: Performance & Scalability (MEDIUM PRIORITY)

> SQLite single-writer and missing connection pooling could bottleneck under load.

- [ ] Evaluate persistent cache backend options (Redis, PostgreSQL) for concurrent workloads
- [ ] Add connection pooling configuration for SQLite persistent cache (WAL mode at minimum)
- [ ] Add configurable concurrency limits per provider
- [ ] Benchmark router strategies under realistic multi-user load
- [ ] Profile memory usage with large file extraction pipeline

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
