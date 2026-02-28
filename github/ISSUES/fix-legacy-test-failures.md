---
title: "Fix 13 Legacy Test Failures (Bedrock, CLI File Loading, Async Streaming)"
labels: ["bug", "tests", "priority: medium"]
assignees: []
milestone: "Phase 8 — Remediation"
---

## Fix 13 Legacy Test Failures

**Priority:** 🟡 MEDIUM — Tests are blind, no production impact
**Estimated effort:** 0.5–1 day
**Branch:** `fix/legacy-test-failures`
**Depends on:** Nothing — can start immediately
**Ref:** [Developer Journal — Feb 26, 2026](../../docs/developer-journal.md)

---

### Context

The full test suite (`pytest -v`) reports **13 failures** that predate the Phase 8.0 work.
All 13 are **test-code issues** — the tests fell out of sync with code changes in
Phases 7.7 (Async-First Conversion) and 7.10 (Catalog Modernization). No production code
is broken; the tests simply assert against stale model IDs, mock the wrong output target,
or set up async mocks incorrectly.

These failures mean 13 tests provide **zero coverage**. Fixing them restores visibility
into the Bedrock provider, CLI file loading, and async streaming code paths.

---

### Checklist

- [x] FIX-1 — Update Bedrock tests for current catalog (3 tests)
- [ ] FIX-2 — Fix CLI file-loading console mock path (9 tests)
- [x] FIX-3 — Fix async streaming mock double-await (1 test)
- [ ] All previously-passing tests still pass
- [ ] No new `ruff` or `mypy` errors introduced

---

### FIX-1 — Bedrock Catalog Drift (3 tests)

| | |
|---|---|
| **File** | `tests/test_bedrock_provider.py` |
| **Root Cause** | Tests reference `amazon.titan-tg1-large`, which was **removed from the catalog** during Phase 7.10 (Catalog Modernization). The Bedrock catalog now contains only Anthropic Claude, Meta Llama, Mistral, Amazon Nova, and Cohere models. |

**Failing tests:**

1. `TestBedrockProviderModels::test_supported_models`
   - Asserts `amazon.titan-tg1-large` is in `get_supported_models()`.
   - The model no longer exists in the catalog.

2. `TestBedrockProviderChatCompletion::test_chat_completion_titan`
   - Sends a chat completion to `amazon.titan-tg1-large`.
   - `validate_model()` rejects it with `InvalidModelError`.

3. `TestBedrockProviderErrorHandling::test_client_error_handling`
   - Asserts the string `"ValidationException"` appears in the raised `ProviderAPIError`.
   - The error message format changed; it now reads
     `"[bedrock] Request validation failed: Invalid request"` — the raw AWS exception
     class name is no longer embedded verbatim.

**Fix:**

```python
# test_supported_models: replace Titan with a current Nova model
- assert "amazon.titan-tg1-large" in models
+ assert "amazon.nova-pro-v1:0" in models

# test_chat_completion_titan: replace with a current Nova model and update
# the mock response format to match the Nova request/response structure
- model="amazon.titan-tg1-large"
+ model="amazon.nova-pro-v1:0"

# test_client_error_handling: assert against the current error format
- assert "ValidationException" in str(exc_info.value)
+ assert "Request validation failed" in str(exc_info.value)
```

- Also audit any remaining references to `titan` in the file and replace with current
  catalog models.
- Verify the Titan request-building test (`test_build_titan_request`) still makes sense
  or should be converted to a Nova request-building test.

**Validation:**
```bash
uv run pytest tests/test_bedrock_provider.py -v
```

---

### FIX-2 — CLI File Loading Console Mock Mismatch (9 tests)

| | |
|---|---|
| **File** | `tests/test_cli_file_loading.py` |
| **Root Cause** | All 9 tests mock `cli.stratifyai_cli.console` and then search `mock_console.print.call_args_list` for specific output strings (`"✓ Loaded"`, `"File not found"`, `"too large"`, etc.). Every assertion finds **zero matches** (`len([]) == 0`), meaning the mock is not intercepting the actual output. |

**Failing tests:**

| # | Test | Expected output |
|---|------|----------------|
| 1 | `TestLoadFileContentSuccess::test_load_valid_small_text_file` | `"✓ Loaded"` |
| 2 | `TestLoadFileContentSuccess::test_load_valid_medium_text_file` | `"✓ Loaded"` |
| 3 | `TestLoadFileContentNotFound::test_file_not_found_error` | `"File not found"` |
| 4 | `TestLoadFileContentSizeLimit::test_file_exceeds_max_size_limit` | `"too large"` |
| 5 | `TestLoadFileContentSizeLimit::test_large_file_warning_with_user_confirmation` | Large file warning |
| 6 | `TestLoadFileContentSizeLimit::test_large_file_warning_with_user_rejection` | Large file warning |
| 7 | `TestLoadFileContentNonTextFile::test_binary_file_raises_unicode_decode_error` | Non-text file error |
| 8 | `TestInteractiveModeInitialFileLoad::test_interactive_mode_loads_initial_file_with_flag` | `"✓ Loaded"` |
| 9 | `TestInteractiveModeInitialFileLoad::test_interactive_mode_continues_without_file_if_load_fails` | `"File not found"` |

**Likely causes (investigate in order):**

1. **Mock path mismatch:** The CLI module may have been refactored so that `console` is
   imported differently (e.g., `from rich.console import Console; console = Console()`
   at module level vs. imported from a shared module). The `@patch` target must match
   the exact module where `console` is **looked up at call time**, not where it is defined.

2. **Output method changed:** The CLI may now use `rich.print()`, `typer.echo()`,
   `click.echo()`, or `rprint()` instead of `console.print()`.

3. **Function signature changed:** The `load_file_content` function (or its callers in
   interactive mode) may have changed its output approach (e.g., returning values instead
   of printing, or using a callback).

**Fix approach:**

1. Read `cli/stratifyai_cli.py` and trace how file-loading messages are emitted.
2. Identify the correct mock target(s).
3. Update all 9 tests to mock the correct output path and assert against the actual
   message format.

**Validation:**
```bash
uv run pytest tests/test_cli_file_loading.py -v
```

---

### FIX-3 — Async Streaming Mock Double-Await (1 test)

| | |
|---|---|
| **File** | `tests/test_async_operations.py` |
| **Root Cause** | The mock wraps an async generator in `AsyncMock(return_value=...)`, creating a double-awaitable. When `chat_completion_stream()` does `await client.chat.completions.create(...)`, it gets back a coroutine that resolves to the async generator — then iterating over it fails with `TypeError: object async_generator can't be used in 'await' expression`. |

**Failing test:**

`TestStreamingAsyncIterator::test_chat_completion_stream_yields_async_iterator`

**The problem in detail:**

```python
# Current (broken) mock setup:
async def async_chunk_iter():
    for chunk in mock_chunks:
        yield chunk

mock_client.chat.completions.create = AsyncMock(return_value=async_chunk_iter())
```

`AsyncMock(return_value=X)` makes the mock an awaitable that resolves to `X`. So
`await mock_client.chat.completions.create(...)` returns the async generator object.
But the **provider code** (after Phase 7.7) expects `create()` to return the async
iterator directly (not wrapped in a coroutine), or the streaming path iterates the
result with `async for chunk in stream:` without an intermediate `await`.

The mismatch is between how the test sets up the mock and how the provider actually
calls and consumes the SDK stream.

**Fix:**

Option A — Use a regular `MagicMock` with a side effect that returns the async generator:
```python
mock_client.chat.completions.create = MagicMock(return_value=async_chunk_iter())
```
This makes `create(...)` return the async generator synchronously (no `await` layer),
which `async for` can iterate directly.

Option B — If the provider does `stream = await client.chat.completions.create(...)`,
keep `AsyncMock` but ensure the async generator is consumed correctly. Trace the actual
provider code path to determine which pattern matches.

**Validation:**
```bash
uv run pytest tests/test_async_operations.py::TestStreamingAsyncIterator -v
```

---

### Acceptance Criteria

- [ ] All 13 previously-failing tests now pass
- [ ] All 340 previously-passing tests still pass
- [ ] Total test count: 357 passing (340 + 13 fixed + 4 skipped)
- [ ] No production code changes required (test-only fix)
- [ ] No new `ruff` or `mypy` errors introduced

### Definition of Done

This issue is complete when `uv run pytest -v` reports **0 failures**.

### Related Issues

- **Context:** Failures surfaced during Phase 8.0 hardening verification
- **Phase 7.7:** Async-First Conversion (caused FIX-3)
- **Phase 7.10:** Catalog Modernization (caused FIX-1)
- **Phase 8.0:** [Critical Bugs & Security Hardening](phase-8.0-critical-bugs-security.md)