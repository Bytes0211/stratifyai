---
title: "Phase 8.1: Consistency & Correctness Fixes"
labels: ["bug", "enhancement", "phase-8.1"]
assignees: []
milestone: "Phase 8 — Remediation"
---

## Phase 8.1: Consistency & Correctness Fixes

**Priority:** 🟡 HIGH — Behavioral correctness
**Estimated effort:** 1–2 days
**Branch:** `fix/phase-8.1-consistency`
**Depends on:** Phase 8.0 (Critical Bugs & Security Hardening)

### Context

Phase 8.0 addresses crash-level bugs and security gaps. This phase focuses on behavioral
inconsistencies and correctness issues that don't crash the system but produce wrong or
surprising results — the kind of problems that erode user trust and make debugging difficult.

These were identified during the comprehensive code review on February 26, 2026.
Full details are documented in `docs/developer-journal.md`.

---

### Task List

- [ ] **8.1.1** — Fix `LLMClient.chat()` missing latency tracking
- [ ] **8.1.2** — Fix Anthropic streaming temperature inconsistency
- [ ] **8.1.3** — Standardize missing-API-key exception type
- [ ] **8.1.4** — Fix `LLMClient` provider auto-detection caching bug
- [ ] **8.1.5** — Sync version number across `__init__.py` and `pyproject.toml`

---

### 8.1.1 — Fix `LLMClient.chat()` missing latency tracking (BUG-5)

**File:** `stratifyai/client.py`

**Problem:**
`client.chat()` non-streaming path calls the provider's `chat_completion()` directly and
returns the response without setting `latency_ms`. However, `client.chat_completion()` wraps
the call with `time.perf_counter()` and does populate `latency_ms`. This means users get
different behavior depending on which method they call — an inconsistency that's hard to
debug and breaks cost/performance dashboards.

```python
# client.py — chat() non-streaming path (missing latency)
async def chat(self, model, messages, ...):
    ...
    return await self._provider_instance.chat_completion(request)  # no timing

# client.py — chat_completion() (has latency)
async def chat_completion(self, request):
    start_time = time.perf_counter()
    response = await self._provider_instance.chat_completion(request)
    response.latency_ms = (time.perf_counter() - start_time) * 1000
    return response
```

**Fix:**
- Add `time.perf_counter()` timing around the provider call in `chat()` non-streaming path
- Set `response.latency_ms` before returning
- Add a unit test asserting `latency_ms is not None` and `latency_ms > 0` for responses
  from both `chat()` and `chat_completion()`

**Validation:**
```bash
pytest tests/test_client.py -v
```

---

### 8.1.2 — Fix Anthropic streaming temperature inconsistency (BUG-7)

**File:** `stratifyai/providers/anthropic.py`

**Problem:**
The non-streaming `chat_completion()` path has careful logic to avoid sending both
`temperature` and `top_p` to Anthropic (which rejects it):

```python
# Non-streaming — correct
if request.temperature != 0.7:
    anthropic_params["temperature"] = request.temperature
elif request.top_p != 1.0:
    anthropic_params["top_p"] = request.top_p
else:
    anthropic_params["temperature"] = request.temperature
```

But the streaming `chat_completion_stream()` path unconditionally sends temperature:

```python
# Streaming — incorrect
anthropic_params = {
    ...
    "temperature": request.temperature,
    ...
}
```

This means streaming requests with a non-default `top_p` will send both parameters,
causing Anthropic API errors that only manifest in streaming mode.

**Fix:**
- Extract the temperature/top_p selection logic into a private method:
  ```python
  def _build_sampling_params(self, request: ChatRequest) -> dict:
      """Build temperature/top_p params respecting Anthropic's mutual exclusivity."""
      if request.temperature != 0.7:
          return {"temperature": request.temperature}
      elif request.top_p != 1.0:
          return {"top_p": request.top_p}
      else:
          return {"temperature": request.temperature}
  ```
- Call `_build_sampling_params()` from both `chat_completion()` and `chat_completion_stream()`
- Add a unit test that mocks a streaming request with `top_p=0.9` and verifies
  `temperature` is NOT in the API call params

**Validation:**
```bash
pytest tests/test_providers_phase2.py -v -k anthropic
pytest tests/test_temperature_unit.py tests/test_temperature_validation.py -v
```

---

### 8.1.3 — Standardize missing-API-key exception type (ARCH-2)

**Files:** All 9 provider `__init__` methods, `stratifyai/api_key_helper.py`

**Problem:**
When an API key is missing, different providers raise different exception types:

| Provider | Exception Raised | Source |
|----------|-----------------|--------|
| OpenAI | `ValueError` | `get_api_key_or_error()` in `api_key_helper.py` |
| Anthropic | `AuthenticationError` | Direct check in `__init__` |
| Google | `AuthenticationError` | Direct check in `__init__` |
| DeepSeek | `AuthenticationError` | Direct check in `__init__` |
| Groq | `AuthenticationError` | Direct check in `__init__` |
| Grok | `AuthenticationError` | Direct check in `__init__` |
| Ollama | `AuthenticationError` | Direct check in `__init__` |
| OpenRouter | `AuthenticationError` | Direct check in `__init__` |
| Bedrock | `ValueError` (or silent pass) | `get_api_key_or_error()` wrapped in try/except |

This means callers can't catch a single exception type for "missing API key". Code like
`except AuthenticationError` will miss OpenAI and Bedrock failures.

**Fix:**
- Update `get_api_key_or_error()` in `api_key_helper.py` to raise `AuthenticationError`
  instead of `ValueError`, preserving the helpful error message with signup URLs and
  alternative provider suggestions
- Update all 9 providers to use `get_api_key_or_error()` instead of manual
  `os.getenv()` + `raise AuthenticationError(provider)` — this gives every provider
  the rich error messages (signup URL, env var name, alternative suggestions)
- Update any tests that currently assert `ValueError` for missing keys
- Update Bedrock's silent `pass` to at minimum log a warning

**Validation:**
```bash
pytest tests/test_cli_auth_error.py tests/test_client.py -v
```

---

### 8.1.4 — Fix `LLMClient` provider auto-detection caching bug (PERF-5)

**File:** `stratifyai/client.py`

**Problem:**
When `LLMClient()` is created without a provider, `chat()` auto-detects the provider
from the model name and initializes `_provider_instance`. But on subsequent calls with a
different model from a different provider, the check `if not self._provider_instance` is
`False` (already initialized), so it skips detection and sends the new model to the
**wrong provider**, causing `InvalidModelError`.

```python
# First call: model="gpt-4o" → detects openai, initializes OpenAIProvider
# Second call: model="claude-3-5-sonnet-20241022" → skips detection, sends to OpenAIProvider → ERROR
async def chat(self, model, messages, ...):
    if not self._provider_instance:          # False on second call!
        provider = self._detect_provider(model)
        self._initialize_provider(provider)
```

**Fix (Option A — re-detect per call):**
- Always detect the provider from the model name
- Compare against the currently initialized provider's `provider_name`
- Re-initialize only if the provider has changed:
  ```python
  detected = self._detect_provider(model)
  if not self._provider_instance or self._provider_instance.provider_name != detected:
      self._initialize_provider(detected)
  ```

**Fix (Option B — multi-provider cache, preferred):**
- Replace `_provider_instance` with `_providers: Dict[str, BaseProvider] = {}`
- On each call, detect provider and check the cache:
  ```python
  detected = self._detect_provider(model)
  if detected not in self._providers:
      self._initialize_provider(detected)  # stores into self._providers[detected]
  provider = self._providers[detected]
  ```
- This avoids re-initializing SDK clients when switching back and forth

**Add test:**
```python
async def test_multi_provider_auto_detection():
    client = LLMClient(api_key="test")
    # Mock both providers
    response1 = await client.chat(model="gpt-4o-mini", messages=[...])
    response2 = await client.chat(model="claude-3-5-sonnet-20241022", messages=[...])
    # Both should succeed without InvalidModelError
```

**Validation:**
```bash
pytest tests/test_client.py -v
```

---

### 8.1.5 — Sync version number across `__init__.py` and `pyproject.toml` (PERF-7)

**Files:** `stratifyai/__init__.py`, `pyproject.toml`

**Problem:**
The package has two version sources that are out of sync:

```python
# stratifyai/__init__.py
__version__ = "0.1.0"     # ← stale

# pyproject.toml
version = "0.1.3"         # ← current
```

The API server reads from `pyproject.toml` at runtime (correct), but anyone doing
`import stratifyai; print(stratifyai.__version__)` gets the wrong value. This will cause
confusion when users report bugs or when version checks are performed.

**Fix:**
Replace the hardcoded version with dynamic resolution from package metadata:

```python
# stratifyai/__init__.py
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("stratifyai")
except PackageNotFoundError:
    __version__ = "0.1.3"  # fallback for editable/development installs
```

This ensures `__version__` always matches `pyproject.toml` without manual synchronization.

**Validation:**
```bash
python -c "import stratifyai; print(stratifyai.__version__)"
# Should print: 0.1.3
```

---

### Acceptance Criteria

- [ ] All existing 303 tests still pass
- [ ] New tests added for each fix (target: +8-10 tests)
- [ ] `latency_ms` is populated consistently from all `LLMClient` entry points
- [ ] All 9 providers raise `AuthenticationError` (not `ValueError`) for missing keys
- [ ] `LLMClient()` without a provider works correctly across provider-switching calls
- [ ] `stratifyai.__version__` matches `pyproject.toml` version
- [ ] No new `ruff` or `mypy` errors introduced
- [ ] Developer journal entry added documenting changes

### Files Affected

| File | Changes |
|------|---------|
| `stratifyai/client.py` | Latency tracking in `chat()`, multi-provider detection cache |
| `stratifyai/providers/anthropic.py` | Extract `_build_sampling_params()`, use in both paths |
| `stratifyai/api_key_helper.py` | Raise `AuthenticationError` instead of `ValueError` |
| `stratifyai/providers/openai.py` | Use `get_api_key_or_error()` (already does) |
| `stratifyai/providers/google.py` | Switch to `get_api_key_or_error()` |
| `stratifyai/providers/deepseek.py` | Switch to `get_api_key_or_error()` |
| `stratifyai/providers/groq.py` | Switch to `get_api_key_or_error()` |
| `stratifyai/providers/grok.py` | Switch to `get_api_key_or_error()` |
| `stratifyai/providers/ollama.py` | Switch to `get_api_key_or_error()` |
| `stratifyai/providers/openrouter.py` | Switch to `get_api_key_or_error()` |
| `stratifyai/providers/bedrock.py` | Improve credential error handling |
| `stratifyai/__init__.py` | Dynamic version from `importlib.metadata` |
| `tests/test_client.py` | New latency + multi-provider tests |
| `tests/test_providers_phase2.py` | Anthropic streaming temperature test |
| `tests/test_cli_auth_error.py` | Update for `AuthenticationError` |

### Related Issues

- Depends on: Phase 8.0 (Critical Bugs & Security Hardening)
- Blocks: Phase 8.2 (Performance & Efficiency), Phase 8.3 (Architecture & Production Readiness)
- Reference: `docs/developer-journal.md` — February 26, 2026 entry