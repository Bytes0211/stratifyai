# Developer Technical Specification: StratifyAI (Workflow + Profiles + MCP)

**Version:** 1.2  
**Date:** 2026-02-28  
**Status:** Draft  
**Audience:** Engineering, Architecture, QA

---

## 1. Scope and Goals

This document provides a comprehensive technical specification for the full StratifyAI workflow and upcoming initiatives:

- **Profiles (Planned):** reusable configuration bundles to normalize behavior across providers.
- **MCP Integration (Planned):** expose StratifyAI as a Model Context Protocol server.

Out of scope: MCP Client that consumes external MCP servers (Phase 9.4 deferred).

---

## 2. Current Baseline (Verified)

- Providers: 9+ provider modules under `stratifyai/providers/`.
- Unified `LLMClient` with async-first architecture and sync wrappers.
- Router with cost/quality/latency/hybrid strategies.
- Prompt templates implemented under `stratifyai/prompts/`.
- REST endpoints for templates under `/api/templates/*`.
- CLI command `stratifyai templates`.
- Web UI with catalog, streaming, file handling.
- No MCP server module exists in the codebase today.

---

## 3. End-to-End Workflow (7-Step Pipeline)

### Step 1: Provider Selection
**Modules:** `stratifyai/providers/*`, `stratifyai/api_key_helper.py`  
**Behavior:**
- Provider explicitly selected or router chooses.
- API key validation performed before execution.

### Step 2: Model Selection
**Modules:** `catalog/models.json`, `catalog/schema.json`, `stratifyai/catalog_manager.py`  
**Behavior:**
- Model metadata includes pricing, context window, capabilities.
- Exposed via API/CLI/UI catalog.

### Step 3: Profile Selection (Planned)
**Modules (new):** `stratifyai/profiles/*`  
**Behavior:**
- Applies a named profile to normalize parameters.
- Validates against model capabilities (vision/tools/json).

### Step 4: Prompt Template Selection
**Modules:** `stratifyai/prompts/*`  
**Behavior:**
- Templates are YAML-driven; render into `list[Message]`.
- `ChatBuilder.with_template()` for programmatic use.

### Step 5: User Input
**Modules:** `stratifyai/utils/file_analyzer.py`, `chunking.py`, `summarization.py`  
**Behavior:**
- Handles text, files, images, multi-turn context.
- Smart chunking + extraction for large files.

### Step 6: Execution
**Modules:** `stratifyai/client.py`, `stratifyai/middleware.py`, `stratifyai/retry.py`  
**Behavior:**
- Async execution with retries and fallback.
- Cost tracking and latency recorded.

### Step 7: Post-Processing (Partial)
**Modules:** `stratifyai/middleware.py`, frontend markdown rendering  
**What exists today:**
- `TrackedLLMClient._post_response()` records cost, logs token/latency metadata, and updates the cost tracker after every non-streaming request — this is an active post-processing stage.
- Budget enforcement via `_pre_request()` blocks calls when budget is exceeded (HTTP 402).
- Markdown rendering and syntax highlighting handled client-side in the Svelte frontend.
- Progressive summarization available as a standalone module (`stratifyai/summarization.py`).

**Planned:**
- JSON validation and schema enforcement on responses (Phase 9.5).
- Backend output normalization across providers.
- Structured field extraction pipeline.

---

## 4. Core Feature Specs

### 4.1 Intelligent Routing
**Module:** `stratifyai/router.py`  
**Strategies:** cost, quality, latency, hybrid  
**Key Methods:** `route()`, `route_for_extraction()`, `get_fallback_chain()`

### 4.2 RAG Pipeline
**Modules:** `stratifyai/rag.py`, `stratifyai/vectordb.py`, `stratifyai/embeddings.py`  
**Capabilities:** ingestion, embeddings, semantic retrieval, citations

### 4.3 Cost Tracking & Budget Enforcement
**Modules:** `stratifyai/cost_tracker.py`, `stratifyai/middleware.py`  
**Behavior:** per-request usage, budget checks, aggregate stats

### 4.4 Caching
**Module:** `stratifyai/caching.py`  
**Behavior:** in-memory + SQLite, TTL, cache stats

### 4.5 ChatBuilder
**Module:** `stratifyai/chat/builder.py`  
**Methods:** `with_model()`, `with_system()`, `with_template()`, etc.

---

## 5. Data Models (Existing + New)

### Provider
- `name: str`
- `api_key_env: str`
- `base_url: str | None`
- `models: list[Model]`
- `capabilities: list[str]`

### Model
- `context: int`
- `cost_input: float`
- `cost_output: float`
- `cost_cache_write: float | None`
- `cost_cache_read: float | None`
- `api_max_input: int | None`
- `supports_vision: bool`
- `supports_tools: bool`
- `supports_caching: bool`
- `reasoning_model: bool`
- `fixed_temperature: float | None`
- `quality_score: float | None`
- `avg_latency_ms: int | None`
- `display_name: str | None`
- `description: str | None`
- `category: str | None`
- `free: bool`
- `deprecated: bool`
- `deprecated_date: date | None`
- `replacement_model: str | None`

### Profile (Planned)
- `name: str`
- `temperature: float | None`
- `max_tokens: int | None`
- `reasoning_depth: str | None` (minimal, standard, deep)
- `speed_vs_accuracy: str | None` (speed, balanced, accuracy)
- `cost_sensitivity: str | None` (low, medium, high)
- `multimodal: bool | None`
- `json_mode: bool | None`
- `tool_use: bool | None`
- `source: "builtin" | "user"`

### PromptTemplate
- `name: str`
- `description: str`
- `system: str`
- `user: str`
- `parameters: list[PromptParameter]`
- `tags: list[str]`
- `recommended_models: list[str]`
- `recommended_temperature: float | None`
- `source: "builtin" | "user"`

### PromptParameter
- `name: str`
- `type: "string" | "text" | "number" | "choice"`
- `description: str`
- `default: Any`
- `required: bool`
- `choices: list[str] | None`

### ChatRequest
- `provider: str`
- `model: str`
- `messages: list[Message]`
- `temperature: float | None`
- `max_tokens: int | None`
- `system: str | None`
- `files: list[File] | None`
- `stream: bool`

### CostRecord
- `timestamp: datetime`
- `provider: str`
- `model: str`
- `input_tokens: int`
- `output_tokens: int`
- `cost_usd: float`
- `latency_ms: float`
- `cached: bool`

---

## 6. Profiles (Planned)

### 6.1 Registry
- Built-ins loaded from `stratifyai/profiles/profiles.yaml`
- User profiles loaded from `~/.stratifyai/profiles/`

### 6.2 Validation Rules
- `multimodal` requires `supports_vision`
- `tool_use` requires `supports_tools`
- `json_mode` requires JSON-capable model
- `fixed_temperature` overrides profile temperature

### 6.3 Integration Points
- `ChatBuilder.with_profile(name)`
- CLI: `stratifyai chat --profile`
- API endpoints under `/api/profiles/*`

### 6.4 Post-Processing Enhancements (Phase 9.5)
- **Scope:** implement centralized response post-processing that validates JSON-mode outputs against schemas, normalizes provider-specific payloads, and supports structured field extraction.
- **Deliverables:** JSON schema registry/utilities, post-processing pipeline module, configuration hooks for enforcing normalization, developer documentation.
- **Dependencies:** Profiles completed (Phase 9); existing cost tracking and middleware remain unchanged.
- **Testing:** add unit tests for schema validation failures, successful normalization paths, and integration coverage ensuring API/CLI use new pipeline when enabled.

---

## 7. MCP Integration (Full Inclusion)

### 7.1 What is MCP
MCP (Model Context Protocol) is a JSON-RPC 2.0 based protocol that standardizes tool/resource access for AI apps.

### 7.2 Transports
- **Streamable HTTP**: for FastAPI deployments
- **Stdio**: for local CLI/editor integration

### 7.3 MCP Primitives
- **Tools**: callable actions
- **Resources**: read-only data via URIs
- **Prompts**: reusable templates (Phase 9.3)

### 7.4 Architecture Alignment
- MCP tools map to `TrackedLLMClient` and `Router`.
- MCP server mounted alongside FastAPI without altering REST endpoints.
- Auth reuse via `STRATIFYAI_API_KEY`.

### 7.5 Phase 10.1 — MCP Server (Core)
**Tools (6):**
- `chat_completion`
- `route_model`
- `count_tokens`
- `list_providers`
- `check_api_keys`
- `get_model_info`

**Resources (5):**
- `stratifyai://catalog/models`
- `stratifyai://catalog/{provider}`
- `stratifyai://cost/summary`
- `stratifyai://providers`
- `stratifyai://version`

### 7.6 Phase 10.2 — MCP Server (Extended)
- Tools: `rag_index`, `rag_query`, `analyze_file`, `route_for_extraction`, `get_cache_stats`
- Prompts: expose prompt templates as MCP Prompts
- Subscriptions: cost summary updates

### 7.7 Phase 10.3 — MCP Client (Deferred)
- Tool execution loop
- Provider tool schema translation
- MCP client manager

### 7.8 Security Model
- Streamable HTTP protected by API key middleware
- Stdio transport uses local environment
- Budget enforcement via `TrackedLLMClient`

### 7.9 Error Handling
- Authentication errors surfaced as descriptive MCP errors
- BudgetExceededError blocks tool execution
- Invalid provider/model errors returned with clear messages

### 7.10 Dependency Impact
- Add `mcp>=1.7.0`
- Transitives: `starlette`, `httpx`, `anyio`, `sse-starlette`

### 7.11 Risk Assessment
- SDK churn → pin dependency
- Auth bypass → middleware
- Cost overruns → budget enforcement
- Transport conflicts → separate mount paths

### 7.12 File Manifest (Planned)
- `stratifyai/mcp_server.py` (new)
- `tests/test_mcp_server.py` (new)
- `docs/MCP-USAGE.md` (new)
- `api/main.py` (mount MCP)
- `requirements.txt`, `pyproject.toml` (dependency add)

### 7.13 Timeline Summary
- Phase 10.1: 1–2 days, 750–950 LOC, 16–20 tests
- Phase 10.2: 1–2 days, 400–550 LOC, 10–15 tests
- Phase 10.3: 3–5 days, 1,200–1,800 LOC, 20–25 tests

---

## 8. API Changes (Planned)

### Profiles
- `GET /api/profiles`
- `GET /api/profiles/{name}`
- `POST /api/profiles/{name}/validate`
- `POST /api/profiles/{name}/resolve`

### MCP
- `/mcp` mount for MCP server

---

## 9. CLI Changes (Planned)

- `stratifyai profiles`
- `stratifyai chat --profile <name>`
- `stratifyai route --profile <name>`

---

## 10. Testing Plan

### Profiles
- `tests/test_profiles.py`: registry, validation, overrides, capability checks

### MCP
- `tests/test_mcp_server.py`: tool/resource handling, auth, prompts exposure

### Regression
- Full suite: `pytest`

---

## 11. Security & Compliance

- API keys via env vars
- `STRATIFYAI_API_KEY` for REST and MCP HTTP
- Input validation on all endpoints
- No secrets in logs

---

## 12. Performance Targets

- p95 response < 2s (non-streaming)
- cold start < 1s for provider init
- memory < 100MB for client instance

---

## 13. Rollout Plan

1. Implement profiles core + registry
2. Add builder/CLI/API integration
3. Implement MCP core server
4. Extend MCP server (RAG + prompts + subscriptions)
5. Update docs and run full test suite

---

## 14. Phase Numbering Cross-Reference

This document and the PRD use a consolidated phase numbering scheme. AGENTS.md uses the original project-internal numbering. Mapping:

- **AGENTS.md Phases 1–7.11** → PRD/DEV-SPEC Phases 1–8 (all complete)
- **AGENTS.md Phase 9.1 (Prompt Templates)** → included in Phases 1–8 (complete)
- **PRD/DEV-SPEC Phase 9 (Profiles)** → new; not in AGENTS.md
- **PRD/DEV-SPEC Phase 9.5 (Post-Processing)** → new; not in AGENTS.md
- **AGENTS.md Phases 9.2–9.4 (MCP)** → PRD/DEV-SPEC Phases 10.1–10.3
- **PRD/DEV-SPEC Phase 11 (Enterprise)** → new; not in AGENTS.md

---

## 15. Open Questions

- Profile precedence with templates and explicit overrides
- Default profile behavior (opt-in vs default)
- MCP tool parameter support for profiles
