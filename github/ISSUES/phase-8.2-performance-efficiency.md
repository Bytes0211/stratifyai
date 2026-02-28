---
title: "Phase 8.2: Performance & Efficiency"
labels: ["performance", "refactor", "phase-8"]
milestone: "Phase 8 — Code Review Remediation"
assignees: []
---

## Phase 8.2: Performance & Efficiency

**Priority:** 🟠 MEDIUM — Maintainability, performance, DRY  
**Estimated effort:** 2–3 days  
**Branch:** `feat/phase-8.2-performance`  
**Depends on:** Phase 8.1 (#phase-8.1)  
**Can run in parallel with:** Phase 8.3

> This phase eliminates large-scale code duplication, adds parallelism to slow paths,
> and removes unnecessary work from hot paths. Combined these changes reduce the
> maintained surface area by ~2,000+ lines and improve throughput for file processing.

---

### Context

The Feb 26 2026 comprehensive code review identified 7 performance and efficiency issues.
This phase addresses the 5 that are independent of architectural changes (the remaining
2 are handled in Phase 8.3). See `docs/developer-journal.md` § "February 26, 2026" for
the full review.

---

### Checklist

- [ ] 8.2.1 — Deduplicate REST and WebSocket handlers (PERF-2)
- [ ] 8.2.2 — Collapse 9 chat modules into generated wrappers (PERF-1)
- [ ] 8.2.3 — Parallelize async chunk summarization (PERF-3)
- [ ] 8.2.4 — Pre-compile router regex patterns (PERF-6)
- [ ] 8.2.5 — Lazy-load provider catalogs (ARCH-1)
- [ ] All 303 existing tests still pass
- [ ] No new `ruff` or `mypy` errors introduced
- [ ] `AGENTS.md` updated if any public API or file structure changed
- [ ] Developer journal entry added

---

### 8.2.1 — Deduplicate REST and WebSocket handlers

| | |
|---|---|
| **ID** | PERF-2 |
| **File** | `api/main.py` |
| **Severity** | Medium |

**Problem**

The `chat_completion` REST handler (~290 lines, L323-612) and the `chat_stream` WebSocket
handler (~216 lines, L616-832) contain massive copy-pasted logic:

- File attachment processing (base64 decode, text extraction)
- Smart chunking with temp file creation and cleanup
- Summarization model selection per provider
- Token count validation with context window checks
- Temperature resolution for reasoning models
- Cost tracking after response

This duplication means every bug fix or feature addition must be applied in two places,
and they have already diverged in subtle ways (e.g., the WebSocket path lacks the detailed
HTTP 413 error responses that the REST path has).

**Fix**

Extract shared logic into private helper functions in `api/main.py` (or a new `api/helpers.py`):

```python
async def _process_file_attachment(
    file_content: str,
    file_name: str,
    provider: str,
    model: str,
    messages: list[Message],
    chunked: bool,
    chunk_size: int,
) -> list[Message]:
    """Decode, optionally chunk, and append file content to messages."""
    ...

def _validate_token_count(
    messages: list[Message],
    provider: str,
    model: str,
    chunked: bool,
) -> None:
    """Raise HTTPException if input exceeds model limits."""
    ...

def _resolve_temperature(
    provider: str,
    model: str,
    requested_temperature: float | None,
) -> float:
    """Return appropriate temperature, forcing 1.0 for reasoning models."""
    ...

def _track_cost(
    cost_tracker: CostTracker,
    response: ChatResponse,
    request_id: str,
) -> None:
    """Record cost entry from a ChatResponse."""
    ...
```

Call these from both the REST and WebSocket handlers. Target: reduce combined handler
code from ~506 lines to ~250 lines.

**Validation**

- REST chat completion works identically before and after
- WebSocket streaming works identically before and after
- File upload + chunking works via both paths
- Token limit errors return the same structured responses from both paths

---

### 8.2.2 — Collapse 9 chat modules into generated wrappers

| | |
|---|---|
| **ID** | PERF-1 |
| **Files** | `stratifyai/chat/stratifyai_openai.py`, `stratifyai/chat/stratifyai_anthropic.py`, `stratifyai/chat/stratifyai_google.py`, `stratifyai/chat/stratifyai_deepseek.py`, `stratifyai/chat/stratifyai_groq.py`, `stratifyai/chat/stratifyai_grok.py`, `stratifyai/chat/stratifyai_openrouter.py`, `stratifyai/chat/stratifyai_ollama.py`, `stratifyai/chat/stratifyai_bedrock.py` |
| **Severity** | Medium |

**Problem**

There are 9 nearly identical `stratifyai_*.py` chat modules, each ~200 lines, totaling
~1,800 lines of duplicated code. They differ only in:

1. The provider name string
2. The environment variable for the API key
3. The module docstring

The `ChatBuilder` and `create_module_builder()` already exist in `builder.py` and can
generate all of this.

**Fix**

Replace each ~200-line module with a thin wrapper (~10 lines):

```python
"""OpenAI chat module.

Usage:
    from stratifyai.chat import openai
    response = await openai.chat("Hello!", model="gpt-4o-mini")
"""
from .builder import create_module_builder

_builder = create_module_builder("openai")

# Public API — preserved for backward compatibility
chat = _builder.chat
chat_stream = _builder.chat_stream
chat_sync = _builder.chat_sync

# Builder chaining methods
with_model = _builder.with_model
with_system = _builder.with_system
with_temperature = _builder.with_temperature
with_max_tokens = _builder.with_max_tokens
with_developer = _builder.with_developer
with_options = _builder.with_options
```

This preserves the exact same public API:
- `from stratifyai.chat import openai` still works
- `openai.chat(...)`, `openai.chat_sync(...)`, `openai.with_model(...)` all still work
- `stratifyai/chat/__init__.py` aliases are unchanged

Net effect: ~1,800 lines → ~180 lines (90% reduction).

**Validation**

```bash
pytest tests/test_chat_builder.py -v
python -c "from stratifyai.chat import openai; print(openai.chat)"
python -c "from stratifyai.chat import anthropic; print(anthropic.with_model)"
```

---

### 8.2.3 — Parallelize async chunk summarization

| | |
|---|---|
| **ID** | PERF-3 |
| **File** | `stratifyai/summarization.py` |
| **Severity** | Medium |

**Problem**

`summarize_chunks_progressive_async()` processes chunks sequentially:

```python
for i, chunk in enumerate(chunks, 1):
    summary = await summarize_chunk_async(chunk, client, model, ...)
    summaries.append(...)
```

For a large file that produces 10 chunks, this means 10 serial LLM calls. Each call
takes 1-5 seconds, so total time is 10-50 seconds. With parallelism this could be
reduced to 2-10 seconds (limited by the slowest chunk).

**Fix**

Replace the sequential loop with bounded parallel execution:

```python
async def summarize_chunks_progressive_async(
    chunks: List[str],
    client: LLMClient,
    model: str = "gpt-4o-mini",
    context: Optional[str] = None,
    show_progress: bool = False,
    max_concurrency: int = 5,
) -> str:
    if not chunks:
        return ""
    if len(chunks) == 1:
        return await summarize_chunk_async(chunks[0], client, model, context=context)

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _summarize_with_limit(i: int, chunk: str) -> str:
        async with semaphore:
            ctx = f"{context} (Part {i}/{len(chunks)})" if context else f"Part {i}/{len(chunks)}"
            return await summarize_chunk_async(chunk, client, model, context=ctx)

    results = await asyncio.gather(
        *[_summarize_with_limit(i, chunk) for i, chunk in enumerate(chunks, 1)]
    )

    summaries = [f"**Part {i}/{len(chunks)}:**\n{r}" for i, r in enumerate(results, 1)]
    combined = "\n\n".join(summaries)

    # Recursive summarization if still too long
    if len(combined) > 10000:
        final_summary = await summarize_chunk_async(
            combined, client, model, context="Combined summaries of document sections"
        )
        return f"**Overall Summary:**\n{final_summary}\n\n**Detailed Summaries:**\n{combined}"

    return combined
```

Key design decisions:
- `max_concurrency=5` prevents overwhelming provider rate limits
- `asyncio.Semaphore` is the standard bounded-concurrency primitive
- Results maintain original ordering (guaranteed by `asyncio.gather`)
- The `max_concurrency` parameter is user-configurable for different providers

**Validation**

```bash
pytest tests/test_phase71.py -v
```

Manual timing: summarize a file with 8+ chunks, compare wall-clock time before/after.

---

### 8.2.4 — Pre-compile router regex patterns

| | |
|---|---|
| **ID** | PERF-6 |
| **File** | `stratifyai/router.py` |
| **Severity** | Low |

**Problem**

`Router._analyze_complexity()` defines ~25 raw regex pattern strings and calls
`re.search(pattern, text)` for each one on every `route()` call. Python's `re.search()`
must compile the pattern each time (the internal cache is limited to 512 patterns and
shared process-wide).

**Fix**

Move patterns to class-level pre-compiled constants:

```python
class Router:
    # Pre-compiled complexity analysis patterns
    _REASONING_PATTERNS = [
        re.compile(r'\banalyze\b', re.IGNORECASE),
        re.compile(r'\bexplain\b', re.IGNORECASE),
        re.compile(r'\breasoning\b', re.IGNORECASE),
        re.compile(r'\bproof\b', re.IGNORECASE),
        re.compile(r'\bstep by step\b', re.IGNORECASE),
        re.compile(r'\bcomplex\b', re.IGNORECASE),
        re.compile(r'\bcalculate\b', re.IGNORECASE),
        re.compile(r'\bderive\b', re.IGNORECASE),
        re.compile(r'\bsolve\b', re.IGNORECASE),
        re.compile(r'\bprove\b', re.IGNORECASE),
        re.compile(r'\bthink\b', re.IGNORECASE),
        re.compile(r'\bcompare\b', re.IGNORECASE),
        re.compile(r'\bevaluate\b', re.IGNORECASE),
        re.compile(r'\bdetailed\b', re.IGNORECASE),
    ]

    _CODE_PATTERNS = [
        re.compile(r'```'),
        re.compile(r'function\s+\w+', re.IGNORECASE),
        re.compile(r'class\s+\w+', re.IGNORECASE),
        re.compile(r'def\s+\w+', re.IGNORECASE),
        re.compile(r'import\s+\w+', re.IGNORECASE),
        re.compile(r'\/\/.*'),
        re.compile(r'\/\*.*\*\/'),
        re.compile(r'\bcode\b', re.IGNORECASE),
    ]

    _MATH_PATTERNS = [
        re.compile(r'\d+\s*[+\-*/]\s*\d+'),
        re.compile(r'\bequation\b', re.IGNORECASE),
        re.compile(r'\bformula\b', re.IGNORECASE),
        re.compile(r'\bcalculus\b', re.IGNORECASE),
        re.compile(r'\balgebra\b', re.IGNORECASE),
        re.compile(r'\bintegral\b', re.IGNORECASE),
    ]
```

Then in `_analyze_complexity()`:

```python
reasoning_matches = sum(1 for p in self._REASONING_PATTERNS if p.search(text))
code_matches = sum(1 for p in self._CODE_PATTERNS if p.search(text))
math_matches = sum(1 for p in self._MATH_PATTERNS if p.search(text))
```

Note: the original code lowercased `text` and used case-sensitive patterns. The fix uses
`re.IGNORECASE` on the compiled patterns, which removes the need for `text.lower()`.

**Validation**

```bash
pytest tests/test_router.py -v
```

---

### 8.2.5 — Lazy-load provider catalogs

| | |
|---|---|
| **ID** | ARCH-1 |
| **Files** | `stratifyai/config.py`, `stratifyai/catalog_manager.py` |
| **Severity** | Low |

**Problem**

All 9 provider catalogs are loaded at module import time in `config.py`:

```python
OPENAI_MODELS: Dict[str, Dict[str, Any]] = get_openai_models()
ANTHROPIC_MODELS: Dict[str, Dict[str, Any]] = get_anthropic_models()
GOOGLE_MODELS: Dict[str, Dict[str, Any]] = get_google_models()
# ... 6 more
```

This means `import stratifyai` immediately reads and parses `catalog/models.json` even
for CLI commands that don't use models (like `check-keys`), scripts that only use one
provider, or test setup phases.

**Fix — Option A: `_CatalogProxy` (preferred)**

Create a dict-like proxy that defers loading until first access:

```python
class _CatalogProxy:
    """Lazy-loading dict proxy for provider model catalogs."""

    def __init__(self, loader):
        self._loader = loader
        self._data = None

    def _ensure_loaded(self):
        if self._data is None:
            self._data = self._loader()

    def __getitem__(self, key):
        self._ensure_loaded()
        return self._data[key]

    def __contains__(self, key):
        self._ensure_loaded()
        return key in self._data

    def get(self, key, default=None):
        self._ensure_loaded()
        return self._data.get(key, default)

    def keys(self):
        self._ensure_loaded()
        return self._data.keys()

    def values(self):
        self._ensure_loaded()
        return self._data.values()

    def items(self):
        self._ensure_loaded()
        return self._data.items()

    def __iter__(self):
        self._ensure_loaded()
        return iter(self._data)

    def __len__(self):
        self._ensure_loaded()
        return len(self._data)

    def __bool__(self):
        self._ensure_loaded()
        return bool(self._data)
```

Then in `config.py`:

```python
OPENAI_MODELS = _CatalogProxy(get_openai_models)
ANTHROPIC_MODELS = _CatalogProxy(get_anthropic_models)
# etc.

MODEL_CATALOG = _CatalogProxy(lambda: {
    "openai": get_openai_models(),
    "anthropic": get_anthropic_models(),
    # ...
})
```

**Fix — Option B: `functools.lru_cache` (simpler)**

The catalog JSON is already cached in `catalog_manager.py`, but the per-provider
extraction functions still run eagerly. Wrapping them adds no benefit since the real
cost is the JSON parse. Option A is preferred because it defers even the function call.

**Validation**

```bash
# Verify import doesn't trigger catalog load
python -c "
import stratifyai
print('Imported successfully')
# Catalog should NOT be loaded yet
from stratifyai.catalog_manager import _CATALOG_CACHE
assert _CATALOG_CACHE is None, 'Catalog loaded too early!'
print('Lazy loading confirmed')
"

# Verify catalog loads on first use
python -c "
from stratifyai.config import OPENAI_MODELS
print(f'OpenAI models: {len(OPENAI_MODELS)} models loaded')
"

pytest -v
```

---

### Acceptance Criteria

- [ ] All 303 existing tests pass — zero regressions
- [ ] New tests added for any new helper functions
- [ ] Combined REST + WebSocket handler code reduced by ~50% (8.2.1)
- [ ] Chat module code reduced by ~90% / ~1,600 lines (8.2.2)
- [ ] Chunk summarization runs in parallel with bounded concurrency (8.2.3)
- [ ] Router regex patterns compiled once at class level (8.2.4)
- [ ] `import stratifyai` does not read `catalog/models.json` (8.2.5)
- [ ] No new `ruff` or `mypy` errors
- [ ] Public API is fully backward-compatible — no breaking changes
- [ ] `AGENTS.md` updated if file structure changed
- [ ] Developer journal entry added

### References

- Developer Journal: `docs/developer-journal.md` § "February 26, 2026"
- Related: Phase 8.0 (critical bugs), Phase 8.1 (consistency), Phase 8.3 (architecture)