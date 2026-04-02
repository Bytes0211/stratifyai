---
title: "Phase 8.3: Architecture & Production Readiness"
labels: ["enhancement", "architecture", "production"]
milestone: "Phase 8 - Remediation"
assignees: []
---

## Phase 8.3 — Architecture & Production Readiness

**Priority:** 💡 MEDIUM-LOW — Long-term maintainability & production hardening
**Estimated effort:** 2–3 days
**Branch:** `feat/phase-8.3-architecture`
**Depends on:** Phase 8.1 (can be worked in parallel with Phase 8.2)

### Context

The [Feb 26 2026 comprehensive code review](../../docs/developer-journal.md) identified 7 architecture improvements that affect long-term maintainability, observability, and production readiness. This phase addresses stale hardcoded metadata, inconsistent logging, missing public exports, bloated dependencies, lack of centralized middleware, ephemeral caching, connection pool waste, and sensitive data leaking through serialization.

These items are lower urgency than Phase 8.0/8.1 but important for a credible PyPI release and production deployments.

### References

- **Review:** `docs/developer-journal.md` — Feb 26, 2026 entry
- **Blocking:** Phase 8.1 must be complete
- **Parallel:** Can be worked alongside Phase 8.2

---

### Task List

#### 8.3.1 — Move router quality/latency scores into catalog
> **IDs:** BUG-6 / ARCH
> **Files:** `stratifyai/router.py`, `catalog/models.json`, `catalog/schema.json`, `scripts/validate_catalog.py`

- [ ] Add `quality_score` (float, 0.0–1.0) and `avg_latency_ms` (int) fields to `catalog/schema.json`
- [ ] Populate values in `catalog/models.json` for **all** models across all 9 providers
- [ ] Update `Router._load_model_metadata()` to read scores from catalog instead of hardcoded dicts
- [ ] Keep hardcoded values as fallback defaults for models missing catalog fields
- [ ] Update `scripts/validate_catalog.py` to warn on missing `quality_score` / `avg_latency_ms`
- [ ] Remove the `quality_scores` and `latency_estimates` hardcoded dicts from `router.py`
- [ ] Verify routing produces sensible results for newer models (grok-4, claude-sonnet-4, gemini-3)

**Why:** The router has hardcoded quality scores and latency estimates for a small subset of models. Many catalog models (grok-4, grok-4-1-fast-reasoning, claude-sonnet-4-20250514, gemini-3, etc.) have no entries and default to `quality_score=0.75` and `latency=2000ms`. This causes the "quality" and "hybrid" routing strategies to produce poor recommendations for newer, better models.

**Validation:**
```bash
python scripts/validate_catalog.py
pytest tests/test_router.py -v
```

---

#### 8.3.2 — Replace `print()` with structured logging
> **ID:** ARCH-3
> **Files:** `stratifyai/cost_tracker.py`, `stratifyai/rag.py`, `stratifyai/summarization.py`, new `stratifyai/logging_config.py`

- [ ] Replace `print(f"⚠️  Budget Alert...")` in `cost_tracker.py` L222 with `logger.warning()`
- [ ] Replace `print(f"Warning: Failed to index...")` in `rag.py` with `logger.warning()`
- [ ] Add `logger = logging.getLogger(__name__)` to every module that currently uses `print()`
- [ ] Create `stratifyai/logging_config.py` with:
  - JSON formatter for production use
  - Human-readable formatter for development
  - `configure_logging(format="json"|"human", level="INFO")` function
- [ ] Grep `stratifyai/` for remaining bare `print(` calls — target: zero

**Why:** The project mixes `print()` statements (cost tracker alerts, RAG warnings) with `logging.getLogger()`. Production systems need consistent structured logging for monitoring, alerting, and log aggregation.

**Validation:**
```bash
grep -rn "print(" stratifyai/stratifyai/ --include="*.py" | grep -v "rprint\|console.print\|__pycache__"
# Should return zero results
```

---

#### 8.3.3 — Expose key utilities in top-level exports
> **ID:** ARCH-4
> **File:** `stratifyai/__init__.py`

- [ ] Add imports to `__init__.py`:
  ```python
  from .utils.token_counter import count_tokens, estimate_tokens
  from .utils.model_selector import ModelSelector
  from .utils.reasoning_detector import is_reasoning_model
  from .catalog_manager import get_catalog_version, load_catalog
  ```
- [ ] Add all new symbols to `__all__`
- [ ] Verify no circular import issues

**Why:** Utilities like `token_counter`, `model_selector`, and `reasoning_detector` are useful public API but require knowledge of the internal package structure to import. Users shouldn't need to know `stratifyai.utils.reasoning_detector` exists.

**Validation:**
```bash
python -c "from stratifyai import count_tokens, estimate_tokens, ModelSelector, is_reasoning_model; print('OK')"
```

---

#### 8.3.4 — Clean up `requirements.txt`
> **ID:** ARCH-5
> **Files:** `requirements.txt`, new `requirements-dev.txt`, `AGENTS.md`

- [ ] Create lean `requirements.txt` with only direct runtime dependencies (~15 packages):
  ```
  openai>=1.12.0
  anthropic>=0.18.0
  google-genai>=1.0.0
  aioboto3>=12.0.0
  boto3>=1.34.0
  python-dotenv>=1.0.0
  pydantic>=2.0.0
  typing-extensions>=4.0.0
  typer>=0.9.0
  tiktoken>=0.5.0
  fastapi>=0.115.0
  uvicorn[standard]>=0.34.0
  websockets>=14.0
  rich>=13.0.0
  ```
- [ ] Create `requirements-dev.txt` with dev/test/build dependencies:
  ```
  -r requirements.txt
  pytest>=9.0.0
  pytest-asyncio>=0.23.0
  pytest-cov>=4.0.0
  pytest-mock>=3.0.0
  ruff>=0.1.0
  mypy>=1.0.0
  chromadb>=0.5.0
  pandas>=2.0.0
  twine>=5.0.0
  ```
- [ ] Update `AGENTS.md` setup instructions to reference both files
- [ ] Update `docs/GETTING-STARTED.md` with separate install commands
- [ ] Verify `pyproject.toml` `[project.optional-dependencies]` stays canonical

**Why:** The current `requirements.txt` is a full `pip freeze` dump with 153 pinned packages including transitive dependencies, dev tools (mypy, ruff, pytest), and publishing tools (twine, wheel). This is fragile for users and confusing.

**Validation:**
```bash
python -m venv /tmp/test-venv
source /tmp/test-venv/bin/activate
pip install -r requirements.txt
python -c "import stratifyai; print('OK')"
deactivate && rm -rf /tmp/test-venv
```

---

#### 8.3.5 — Add centralized request/response middleware
> **ID:** ARCH-7
> **Files:** New `stratifyai/middleware.py`, `api/main.py`

- [ ] Create `stratifyai/middleware.py` with `TrackedLLMClient` class that wraps `LLMClient`:
  - **Pre-request:** Log request metadata (provider, model, estimated tokens)
  - **Pre-request:** Check `CostTracker.is_over_budget()` → raise `BudgetExceededError`
  - **Timing:** Wrap every call with `time.perf_counter()` and set `latency_ms`
  - **Post-response:** Call `CostTracker.add_entry()` automatically
  - **Post-response:** Log response metadata (tokens used, cost, latency)
- [ ] Update `api/main.py` to use `TrackedLLMClient` instead of manual tracking code
- [ ] This complements the handler deduplication from Phase 8.2.1
- [ ] Add unit tests for the middleware wrapper

**Why:** Logging, latency tracking, cost tracking, and budget enforcement are currently done ad-hoc in both API handlers with copy-pasted code. A centralized middleware provides consistent observability and makes it impossible to forget tracking in new endpoints.

**Validation:**
```bash
pytest tests/test_client.py -v
# Verify API still tracks costs correctly after middleware integration
```

---

#### 8.3.6 — Add persistent cache option
> **ID:** PERF-4
> **File:** `stratifyai/caching.py`

- [ ] Create `PersistentResponseCache` subclass backed by SQLite:
  - `__init__(self, db_path="~/.stratifyai/cache.db", ttl=3600, max_size=1000)`
  - Same `get()` / `set()` / `clear()` / `get_stats()` / `get_entries()` interface
  - Serialize `ChatResponse` to JSON for storage (handle `datetime` fields)
  - Create table schema: `(key TEXT PRIMARY KEY, response_json TEXT, timestamp REAL, hits INTEGER, cost_saved REAL)`
  - Respect TTL on reads (delete expired entries)
  - Respect max_size on writes (evict oldest)
- [ ] Keep in-memory `ResponseCache` as default — no breaking changes
- [ ] Add `cache_backend` parameter to `cache_response()` decorator
- [ ] Add unit tests: set → get → restart (new instance) → get (should find it)
- [ ] Document usage in `docs/StratifyAI-Prompt-Caching.md`

**Why:** The current `ResponseCache` is in-memory only — every server restart loses all cached responses. For production systems, this limits the cache's value significantly.

**Deferred:** Redis backend support (future enhancement)

**Validation:**
```bash
pytest tests/test_caching.py tests/test_phase74_caching.py -v
```

---

#### 8.3.7 — Provider instance connection pooling
> **ID:** ARCH-6
> **File:** `stratifyai/client.py`

- [ ] Add module-level `_provider_pool: Dict[str, BaseProvider] = {}` in `client.py`
- [ ] Update `_initialize_provider()` to check pool first before creating new instance
- [ ] Add `LLMClient.close()` method to release the provider (remove from pool)
- [ ] Add async context manager support (`__aenter__` / `__aexit__`)
- [ ] Add module-level `close_all_providers()` to shut down all pooled connections
- [ ] Export `close_all_providers` from `stratifyai/__init__.py`
- [ ] Add tests verifying only one SDK client is created per provider across multiple `LLMClient` instances

**Why:** Each `LLMClient` creates a fresh `AsyncOpenAI` / `AsyncAnthropic` / etc. client. The API server's `get_client()` cache helps, but library users who create multiple `LLMClient` instances waste connection pool resources and may hit rate limits faster.

**Validation:**
```bash
pytest tests/test_client.py -v
# + manual verification: create 3 LLMClient("openai"), verify only 1 AsyncOpenAI instance exists
```

---

#### 8.3.8 — Exclude `raw_response` from serialization by default
> **ID:** SEC-6
> **File:** `stratifyai/models.py`, `api/main.py`

- [ ] Add `to_dict(include_raw: bool = False) -> dict` method on `ChatResponse`:
  ```python
  def to_dict(self, include_raw: bool = False) -> dict:
      d = {
          "id": self.id,
          "model": self.model,
          "content": self.content,
          "finish_reason": self.finish_reason,
          "usage": { ... },
          "provider": self.provider,
          "created_at": self.created_at.isoformat(),
          "latency_ms": self.latency_ms,
      }
      if include_raw:
          d["raw_response"] = self.raw_response
      return d
  ```
- [ ] Update API handlers to use `to_dict()` when building response dicts
- [ ] Keep `raw_response` available as an attribute for programmatic/debugging use
- [ ] Document in docstring that `raw_response` should not be logged in production
- [ ] Add test verifying `to_dict()` excludes `raw_response` by default

**Why:** `ChatResponse.raw_response` may contain system fingerprints, internal IDs, or other sensitive metadata from providers. It's included in every response object and could leak if responses are serialized, stored, or logged.

**Validation:**
```bash
pytest tests/test_models.py -v
# Verify API JSON responses don't include raw_response field
```

---

### Acceptance Criteria

- [ ] All existing 303 tests still pass
- [ ] New tests added for each item (target: +10–15 tests)
- [ ] No new `ruff` or `mypy` errors introduced
- [ ] `AGENTS.md` updated to reflect new files, exports, and setup changes
- [ ] Developer journal entry added documenting what was done
- [ ] `grep -rn "print(" stratifyai/stratifyai/` returns zero non-CLI results
- [ ] `python -c "import stratifyai"` does NOT trigger `catalog/models.json` read
- [ ] API responses do not include `raw_response` field

### Files Changed (Expected)

| Action | File |
|--------|------|
| Modified | `stratifyai/router.py` |
| Modified | `catalog/models.json` |
| Modified | `catalog/schema.json` |
| Modified | `scripts/validate_catalog.py` |
| Modified | `stratifyai/cost_tracker.py` |
| Modified | `stratifyai/rag.py` |
| Modified | `stratifyai/summarization.py` |
| Created | `stratifyai/logging_config.py` |
| Modified | `stratifyai/__init__.py` |
| Modified | `requirements.txt` |
| Created | `requirements-dev.txt` |
| Modified | `AGENTS.md` |
| Modified | `docs/GETTING-STARTED.md` |
| Created | `stratifyai/middleware.py` |
| Modified | `api/main.py` |
| Modified | `stratifyai/caching.py` |
| Modified | `stratifyai/client.py` |
| Modified | `stratifyai/models.py` |
| Modified | `docs/StratifyAI-Prompt-Caching.md` |
| Added | `tests/test_middleware.py` |
| Added | `tests/test_persistent_cache.py` |

### Technical Debt Resolved

- ✅ Stale hardcoded router metadata for only a subset of models
- ✅ Inconsistent print/logging mix across modules
- ✅ Hidden utility APIs requiring internal path knowledge
- ✅ 153-package bloated requirements.txt
- ✅ Ad-hoc observability/tracking scattered across handlers
- ✅ Ephemeral cache lost on every restart
- ✅ Wasted connection pools from duplicate SDK clients
- ✅ Sensitive raw_response data leaking through serialization

### Technical Debt Incurred

- ⏳ Persistent cache is SQLite-only (Redis support deferred)
- ⏳ Quality scores in catalog are still manually estimated (real benchmark integration deferred)
- ⏳ `TrackedLLMClient` middleware doesn't yet support streaming cost tracking
- ⏳ Connection pool doesn't implement max-idle timeout or health checks