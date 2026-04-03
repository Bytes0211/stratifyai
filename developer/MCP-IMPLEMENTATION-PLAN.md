# MCP Server Implementation Plan

Date: 2026-04-03  
Branch: `feat/mcp-implementation`  
Reference: `developer/PRD-MCP-implemenation.md` (v1.2)

---

## Pre-Work Decisions (Resolve Before Writing Code)

The PRD leaves four open questions. Resolve these before Phase 1 begins.

| # | Question | Decision |
|---|----------|----------|
| OQ-1 | Include raw provider payload behind a debug flag? | **No** for v1. Add `debug: bool = False` input to `chat_completion` but omit raw payload; reserved for post-GA. |
| OQ-2 | `chat_with_routing` support provider allow/deny lists? | **Yes** — pass `preferred_providers` and `excluded_providers` straight to `Router.__init__`. Already supported by existing router. |
| OQ-3 | Streamable HTTP in initial GA or post-GA? | **Post-GA**. Phase 6 remains optional and will not block the GA checklist. |
| OQ-4 | Expose all prompt templates or approved subset? | **All** — expose whatever is in the registry. No manual allowlist needed at v1. |

---

## Package / Dependency Decisions

- SDK: `mcp[cli]` (FastMCP pattern), pinned to `>=1.25,<2` (v2 has breaking changes).
- Optional dependency group `mcp`; extend `all` extras to include it.
- New `stratifyai/mcp_server/` sub-package — **not** added to default imports in `stratifyai/__init__.py`.
- `pyproject.toml` script entry: `stratifyai-mcp = "stratifyai.mcp_server.__main__:main"`.
- `setuptools` packages list: add `stratifyai.mcp_server`, `stratifyai.mcp_server.prompts`, `stratifyai.mcp_server.utils` (if needed).

---

## Phase Roadmap

```
Phase 0 — Contract Freeze       (this document + PRD  ✅  planning only)
Phase 1 — Server Bootstrap      (scaffold + entrypoint)
Phase 2 — Core Tools            (chat + routing + model tools)
Phase 3 — Cost/Validation Tools (cost summary + validate + estimate)
Phase 4 — Resources             (catalog + providers + costs + strategies)
Phase 5 — Prompt Exposure       (MCP prompt primitives)
Phase 6 — HTTP Transport        (optional — post-GA)
Phase 7 — Tests + CI gates
Phase 8 — Docs + Client Setup
```

---

## Phase 0 — Contract Freeze ✅

**Status:** Complete (PRD v1.2 + this plan)

Deliverables already done:
- Tool list, argument names, and return shapes defined in PRD §7.
- Error code mapping defined in PRD §8.
- Schema versioning strategy: `mcp_schema_version = 1` constant in `schemas.py`.

**Nothing to implement in this phase.**

---

## Phase 1 — Server Bootstrap

### Goal
`stratifyai-mcp` command starts cleanly. An MCP client can connect and see zero tools/resources/prompts (they come later).

### Files to Create

| File | Purpose |
|------|---------|
| `stratifyai/mcp_server/__init__.py` | Package marker; export `create_server` |
| `stratifyai/mcp_server/__main__.py` | `main()` entry — parse args, call `server.run()` |
| `stratifyai/mcp_server/server.py` | `FastMCP` app init; compose tools/resources/prompts modules |
| `stratifyai/mcp_server/schemas.py` | Typed Pydantic models for all tool inputs/outputs; `mcp_schema_version = 1` |
| `stratifyai/mcp_server/errors.py` | Error code enum + `mcp_error()` factory that maps StratifyAI exceptions → structured MCP errors |

### Files to Modify

| File | Change |
|------|--------|
| `pyproject.toml` | Add `[project.optional-dependencies] mcp = ["mcp[cli]>=1.0.0"]`; add to `all` extras; add script entry |
| `pyproject.toml` `[tool.setuptools] packages` | Append `"stratifyai.mcp_server"` |

### server.py structure

```python
from mcp.server.fastmcp import FastMCP
from stratifyai.mcp_server import tools, resources, prompts

mcp = FastMCP("stratifyai", version="1.0.0")

tools.register(mcp)
resources.register(mcp)
prompts.register(mcp)
```

### __main__.py structure

```python
import argparse
from stratifyai.mcp_server.server import mcp

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    args = parser.parse_args()
    mcp.run(transport=args.transport)

if __name__ == "__main__":
    main()
```

### errors.py contract

```python
class MCPErrorCode(str, Enum):
    AUTH_FAILED        = "auth_failed"
    INVALID_PROVIDER   = "invalid_provider"
    INVALID_MODEL      = "invalid_model"
    BUDGET_EXCEEDED    = "budget_exceeded"
    PROVIDER_ERROR     = "provider_error"
    RATE_LIMITED       = "rate_limited"
    CONTENT_TOO_LARGE  = "content_too_large"
    INTERNAL_ERROR     = "internal_error"

# Maps StratifyAI exception classes → MCPErrorCode
EXCEPTION_MAP: dict[type[Exception], MCPErrorCode] = { ... }

def mcp_error(exc: Exception, provider: str | None, model: str | None) -> dict:
    # Sanitizes message (reuse stratifyai.utils.sanitizer)
    # Returns: {error_code, error_type, message, provider, model}
```

### Acceptance Criteria
- [ ] `python -m stratifyai.mcp_server` starts without error.
- [ ] `stratifyai-mcp` CLI entry is importable after `pip install -e ".[mcp]"`.
- [ ] An MCP inspector session connects and lists 0 tools, 0 resources, 0 prompts.

---

## Phase 2 — Core Tools

### Goal
Implement the five highest-value execution tools. MCP client can call chat and routing.

### Files to Create

| File | Purpose |
|------|---------|
| `stratifyai/mcp_server/tools.py` | All tool registrations; imports from StratifyAI core |

### Tool Implementations (in `tools.py`)

#### `chat_completion`
```
Inputs  (ChatCompletionInput schema):
  provider: str
  model: str
  messages: list[{role, content}]
  temperature: float | None = None
  max_tokens: int | None = None
  stream: bool = False          # v1: ignored (MCP stdio doesn't stream mid-call)

Core call:
  client = LLMClient(provider=provider, api_key=_resolve_key(provider))
  response = await client.chat_completion(ChatRequest(...))

Output (ChatCompletionOutput schema):
  content: str
  provider: str
  model: str
  prompt_tokens: int
  completion_tokens: int
  total_tokens: int
  cost_usd: float
  latency_ms: float | None
  mcp_schema_version: int = 1
```

#### `chat_with_routing`
```
Inputs (ChatWithRoutingInput schema):
  messages: list[{role, content}]
  strategy: "cost" | "quality" | "latency" | "hybrid" = "hybrid"
  capabilities: list[str] | None = None
  preferred_providers: list[str] | None = None
  excluded_providers: list[str] | None = None
  max_cost_usd: float | None = None
  max_latency_ms: float | None = None

Core call:
  router = Router(strategy=strategy, preferred_providers=..., excluded_providers=...)
  route_result = router.route(messages, required_capabilities=capabilities)
  client = LLMClient(provider=route_result.provider, ...)
  response = await client.chat_completion(...)

Output (ChatWithRoutingOutput schema):
  selected_provider: str
  selected_model: str
  routing_strategy: str
  content: str
  prompt_tokens: int
  completion_tokens: int
  cost_usd: float
  latency_ms: float | None
  mcp_schema_version: int = 1
```

#### `list_providers`
```
Inputs: none
Core call: catalog_manager.load_catalog() — keys are provider names
Output: list of {provider: str, model_count: int, configured: bool}
  configured = bool(os.environ.get(f"{PROVIDER}_API_KEY"))
```

#### `list_models`
```
Inputs (ListModelsInput): provider: str
Core call: MODEL_CATALOG.get(provider, {})
Output: list of {model_id, context_window, cost_input_per_1m, cost_output_per_1m, capabilities[]}
```

#### `get_model_info`
```
Inputs (ModelInfoInput): provider: str, model: str
Core call: MODEL_CATALOG.get(provider, {}).get(model)
Output: full model metadata dict + mcp_schema_version
```

### Exception Handling Pattern (apply to all tools)

```python
@mcp.tool()
async def chat_completion(input: ChatCompletionInput) -> ChatCompletionOutput:
    try:
        # ... core call ...
    except (AuthenticationError, ProviderError, ...) as exc:
        raise ValueError(json.dumps(mcp_error(exc, input.provider, input.model)))
```

Note: FastMCP converts `ValueError` with JSON detail into a structured tool error.

### Acceptance Criteria
- [ ] All five tools appear in `mcp.tools` list on server startup.
- [ ] `chat_completion` with a valid provider/model executes and returns correct schema.
- [ ] Invalid provider returns structured error with `error_code: "invalid_provider"`.
- [ ] Invalid model returns structured error with `error_code: "invalid_model"`.
- [ ] `list_models` for a known provider returns ≥ 1 entry.

---

## Phase 3 — Cost and Validation Tools

### Goal
Expose financial and readiness observability.

### Tools to Add (in `tools.py`)

#### `get_cost_summary`
```
Inputs (CostSummaryInput):
  provider: str | None = None
  model: str | None = None

Core call:
  tracker = _get_global_tracker()   # module-level CostTracker singleton in mcp_server
  summary = tracker.get_summary()
  # filter by provider/model if specified

Output:
  total_cost_usd: float
  total_calls: int
  total_tokens: int
  by_provider: dict[str, float]
  by_model: dict[str, float]
  mcp_schema_version: int = 1
```

Note: Add a module-level `_mcp_cost_tracker = CostTracker()` in `tools.py`; pass it to `LLMClient` in `chat_completion` / `chat_with_routing`.

#### `validate_provider`
```
Inputs (ValidateProviderInput): provider: str

Core call:
  from stratifyai.utils.provider_validator import validate_provider_availability
  result = validate_provider_availability(provider)

Output:
  provider: str
  configured: bool            # API key present
  models_available: list[str] # from catalog
  validation_errors: list[str]
  mcp_schema_version: int = 1
```

#### `estimate_cost`
```
Inputs (EstimateCostInput):
  provider: str
  model: str
  message_text: str

Core call:
  from stratifyai.utils.token_counter import estimate_tokens
  from stratifyai.config import MODEL_CATALOG
  tokens = estimate_tokens(message_text)
  model_info = MODEL_CATALOG[provider][model]
  cost = (tokens / 1_000_000) * model_info["cost_input"]

Output:
  estimated_input_tokens: int
  estimated_cost_usd: float
  provider: str
  model: str
  mcp_schema_version: int = 1
```

### Acceptance Criteria
- [ ] `get_cost_summary` returns zero totals on fresh tracker (no prior calls).
- [ ] `get_cost_summary` totals update after a `chat_completion` tool call in the same session.
- [ ] `validate_provider` returns `configured: False` when env key is absent.
- [ ] `estimate_cost` returns a positive float for any non-empty message.

---

## Phase 4 — Resource Layer

### Goal
MCP resources deliver catalog and config context to clients without requiring a tool call.

### Files to Create

| File | Purpose |
|------|---------|
| `stratifyai/mcp_server/resources.py` | MCP resource registrations |

### Resources to Implement

| URI | Content | Core source |
|-----|---------|-------------|
| `stratifyai://catalog` | Full `catalog/models.json` as JSON | `load_catalog()` |
| `stratifyai://catalog/{provider}` | Single-provider model dict | `MODEL_CATALOG[provider]` |
| `stratifyai://providers` | Provider list + configured status | os.environ checks |
| `stratifyai://costs` | Current session cost summary | `_mcp_cost_tracker.get_summary()` |
| `stratifyai://router/strategies` | Enum values + descriptions | `RoutingStrategy` + docstrings |

### Resource Pattern

```python
@mcp.resource("stratifyai://catalog")
async def catalog_resource() -> str:
    return json.dumps(load_catalog(), indent=2)

@mcp.resource("stratifyai://catalog/{provider}")
async def catalog_provider_resource(provider: str) -> str:
    data = MODEL_CATALOG.get(provider)
    if data is None:
        raise ValueError(f"Unknown provider: {provider}")
    return json.dumps(data, indent=2)
```

### Acceptance Criteria
- [ ] All five resource URIs appear in MCP resource list.
- [ ] `stratifyai://catalog` returns valid JSON matching `catalog/schema.json`.
- [ ] `stratifyai://catalog/openai` returns only OpenAI models.
- [ ] `stratifyai://catalog/unknown` returns structured error.
- [ ] `stratifyai://router/strategies` lists all four strategies.

---

## Phase 5 — Prompt Exposure

### Goal
Register StratifyAI prompt templates as MCP prompt primitives.

### Files to Create

| File | Purpose |
|------|---------|
| `stratifyai/mcp_server/prompts.py` | MCP prompt registrations |

### Prompt Implementations

Three named prompts mirror the PRD spec. All other registry templates are exposed dynamically.

#### `compare_models`
```
Arguments: models (required, list of "provider/model" strings)
Core: registry.render("chatbot", ...) or build custom message array
Output: list of MCP {role, content} messages describing comparison task
```

#### `recommend_model`
```
Arguments: task_description (required), budget (optional), priority (optional: cost|quality|latency)
Output: messages that guide the LLM to recommend a model
```

#### `analyze_costs`
```
Arguments: time_period (optional)
Output: messages that guide cost analysis using current session data
```

#### Dynamic registry prompts
For every template returned by `registry.list()`, register an MCP prompt using the template name and its declared parameters:

```python
def register(mcp: FastMCP) -> None:
    # Named prompts
    _register_compare_models(mcp)
    _register_recommend_model(mcp)
    _register_analyze_costs(mcp)
    # Dynamic: expose all registry templates
    for template in registry.list():
        _register_template_prompt(mcp, template)
```

### Acceptance Criteria
- [ ] Three named prompts (`compare_models`, `recommend_model`, `analyze_costs`) present.
- [ ] All 10 built-in templates also present as callable MCP prompts.
- [ ] Each prompt returns a `list[{role, content}]` response, not raw strings.
- [ ] User-defined templates in `~/.stratifyai/prompts/` also appear (inherited from registry).

---

## Phase 6 — HTTP Transport (Post-GA, Optional)

Not a blocking phase. Skip for initial GA.

When scoped:
- Add `--transport streamable-http` flag to `__main__.py` (already stubbed in Phase 1).
- Add `--host` and `--port` flags.
- Add local auth guidance to docs (bearer token via `STRATIFYAI_MCP_TOKEN` env var).
- Add HTTP integration tests.

---

## Phase 7 — Tests and CI Gates

### Test File Layout

```
tests/
  test_mcp_schemas.py        — Phase 1: Pydantic model validation, error factory
  test_mcp_tools.py          — Phase 2+3: all tools with mocked LLMClient/Router/CostTracker
  test_mcp_resources.py      — Phase 4: resource content and error cases
  test_mcp_prompts.py        — Phase 5: prompt registration and output shape
  test_mcp_integration.py    — marked integration: full session via MCP SDK test client
```

### Test Strategy Per Phase

**Phase 1 — schemas.py / errors.py**
- Pydantic validation: required fields, optional defaults, type coercion.
- `mcp_error()` factory: each `EXCEPTION_MAP` entry maps to correct `MCPErrorCode`.
- Sanitizer: no API key leaks in error output.

**Phase 2 — tools: execution path**
- Mock `LLMClient.chat_completion` to return a fixture `ChatResponse`.
- Assert output schema fields are populated correctly.
- Assert `chat_with_routing` extracts `selected_provider`/`selected_model` from router result.
- Assert error path: `AuthenticationError` → `error_code == "auth_failed"`.

**Phase 3 — tools: cost/validation**
- `get_cost_summary`: fresh tracker returns zero; after injecting a `CostEntry` returns correct totals.
- `estimate_cost`: known token count for known string returns expected cost given catalog pricing.
- `validate_provider`: mock env variable presence/absence.

**Phase 4 — resources**
- `catalog_resource()` output round-trips through `catalog/schema.json` JSON schema validator.
- `catalog_provider_resource("openai")` returns only keys present in OpenAI section of catalog.
- `catalog_provider_resource("nonexistent")` raises `ValueError`.

**Phase 5 — prompts**
- Every registered prompt returns `list[dict]` with `role` and `content` keys.
- Dynamic prompts: count of registered prompts == 3 named + `len(registry.list())`.

**Phase 7 — integration (marked `integration`)**
- Create in-process MCP client session using MCP test utilities.
- Call `list_providers` → non-empty response.
- Call `estimate_cost` for openai/gpt-4.1-mini → positive float.
- Fetch `stratifyai://router/strategies` → valid JSON.

### CI Gate Changes

Add to `.github/workflows/` test job:
- `pip install -e ".[dev,mcp]"` (add `mcp` to install extras).
- Run `tests/test_mcp_*.py` (excluding `test_mcp_integration.py` unless `MCP_INTEGRATION=true`).
- Coverage threshold: 80% on `stratifyai/mcp_server/`.

### Acceptance Criteria
- [ ] All unit tests pass without `integration` marker.
- [ ] No regressions in existing 536-test suite.
- [ ] `mypy stratifyai/mcp_server` passes.
- [ ] `ruff check stratifyai/mcp_server` passes.

---

## Phase 8 — Docs and Client Setup

### Files to Create

| File | Content |
|------|---------|
| `docs/MCP-QUICKSTART.md` | Install, configure, first tool call in < 15 min |
| `docs/MCP-TOOLS-REFERENCE.md` | All tools with input/output schemas and examples |
| `docs/MCP-CLIENT-CONFIG.md` | Claude Desktop, Claude Code, Cursor, VS Code Copilot Chat config blocks |

### Claude Desktop config block (to include in docs)

```json
{
  "mcpServers": {
    "stratifyai": {
      "command": "stratifyai-mcp",
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

### Acceptance Criteria
- [ ] New contributor can configure Claude Desktop and call `get_model_info` within 15 minutes using docs alone.
- [ ] README links to MCP quickstart doc.

---

## GA Checklist

Execute in order after Phase 8:

- [ ] Zero P0/P1 defects open.
- [ ] All MCP unit tests green in CI.
- [ ] Integration test confirmed against Claude Desktop and one other MCP client.
- [ ] `stratifyai://catalog` resource output validated against `catalog/schema.json`.
- [ ] `mcp_schema_version = 1` constant frozen and documented.
- [ ] `docs/CHANGELOG.md` entry added.
- [ ] `AGENTS.md` project status updated to reflect MCP GA.

---

## Dependency Map (What Blocks What)

```
Phase 0 (plan)
  └─► Phase 1 (scaffold)
        └─► Phase 2 (core tools)
              ├─► Phase 3 (cost/validation tools)
              ├─► Phase 4 (resources)
              └─► Phase 5 (prompts)
                    └─► Phase 7 (tests + CI)  ← requires all of 1–5
                          └─► Phase 8 (docs)
Phase 6 (HTTP) is independent — can be done any time after Phase 1
```

Phases 3, 4, and 5 can be worked in parallel once Phase 2 is done.

---

## Key Existing Modules Referenced by MCP Layer

| MCP need | Existing module | Import path |
|----------|----------------|-------------|
| Multi-provider chat | `LLMClient` | `stratifyai.client` |
| Routing | `Router`, `RoutingStrategy` | `stratifyai.router` |
| Model catalog | `MODEL_CATALOG`, `load_catalog` | `stratifyai.config`, `stratifyai.catalog_manager` |
| Cost tracking | `CostTracker` | `stratifyai.cost_tracker` |
| Token estimation | `estimate_tokens`, `count_tokens_for_messages` | `stratifyai.utils.token_counter` |
| Prompt templates | `registry` | `stratifyai.prompts` |
| Provider validation | `validate_provider_availability` | `stratifyai.utils.provider_validator` |
| Error sanitization | `sanitize_error` | `stratifyai.utils.sanitizer` |
| Reasoning detection | `is_reasoning_model` | `stratifyai.utils.reasoning_detector` |

No business logic lives in `mcp_server/`. The layer is wiring only.
