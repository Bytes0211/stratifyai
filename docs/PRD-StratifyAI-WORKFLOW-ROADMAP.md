# Product Requirements Document: StratifyAI (Workflow + Profiles + MCP)

**Version:** 1.2  
**Date:** 2026-02-28  
**Status:** Draft  
**Audience:** Business Analysts, Product Owners, Business Stakeholders

---

## 1. Executive Summary

StratifyAI is a unified LLM orchestration framework that abstracts provider differences and delivers a predictable, auditable workflow for AI applications. This PRD fully integrates the StratifyAI workflow scope with two strategic initiatives:

1. **Profiles** — reusable configuration bundles that standardize behavior across providers and models.  
2. **MCP Integration** — expose StratifyAI through the Model Context Protocol to unlock MCP-native clients (Claude Desktop, Cursor, Warp).

These initiatives complete the product workflow and expand ecosystem adoption without sacrificing provider flexibility.

---

## 2. App Overview and Objectives

### What is StratifyAI?

StratifyAI provides a single, consistent interface for 9+ providers (OpenAI, Anthropic, Google Gemini, AWS Bedrock, DeepSeek, Groq, Grok, OpenRouter, Ollama). It decouples prompt logic from provider SDKs and adds routing, cost management, and production-grade workflows.

### Core Objectives

- **Provider Abstraction:** One API surface across providers.  
- **Predictable Behavior via Profiles:** Standardized configuration bundles independent of provider/model.  
- **Prompt Reusability:** YAML-based templates for common tasks.  
- **Intelligent Routing:** Cost/quality/latency/hybrid selection.  
- **Cost Visibility:** Per-request + aggregate tracking with budget enforcement.  
- **Production Readiness:** Streaming, caching, retries, error handling, large-file processing.

### Problem Statement

Teams building on LLMs face fragmented APIs, inconsistent behavior across models, unpredictable costs, and painful provider migrations. StratifyAI solves this by providing a unified pipeline:

**Provider → Model → Profile → Prompt Template → User Input → Execution → Post-Processing**

This pipeline makes every request predictable, auditable, and portable.

---

## 3. Target Audience

| Audience | Need |
|---------|------|
| Backend developers | Use multiple providers without rewriting SDK logic |
| AI/ML engineers | Compare models, route intelligently, manage cost/quality |
| Product teams | Consistent outputs across models and providers |
| Enterprise teams | Governance, spend controls, security compliance |
| Solo devs/startups | Best models without lock-in or rework |
| DevOps/platform | Observability, caching, reliability |

---

## 4. Core Features and Functionality

### 4.1 Unified Pipeline (7-Step Workflow)

#### Step 1: Provider Selection
- **Description:** Choose the API provider (OpenAI, Anthropic, Google, Bedrock, DeepSeek, Groq, Grok, OpenRouter, Ollama).
- **Implementation:** Provider modules under `stratifyai/providers/` implement `BaseProvider` abstract class. Auto-detection from API key availability.
- **Acceptance Criteria:**
  - User can explicitly select a provider or let the router choose.
  - Provider availability is validated before execution.
  - Missing API keys produce clear error messages with setup instructions.

#### Step 2: Model Selection
- **Description:** Select a specific model within the chosen provider.
- **Implementation:** Community-maintained model catalog (`catalog/models.json`) with capability metadata, context windows, and pricing. Validated by JSON schema (`catalog/schema.json`).
- **Acceptance Criteria:**
  - Models are browsable via API (`GET /api/models`), CLI, and web UI catalog tab.
  - Each model entry includes: provider, context window, capabilities (vision, reasoning, tool use), and cost per token.
  - Auto model selection available for file extraction tasks (`stratifyai/utils/model_selector.py`).

#### Step 3: Profile Selection (Planned)
- **Status:** Not yet implemented.
- **Description:** Profiles are reusable configuration bundles that standardize model behavior independent of the provider/model.
- **Planned Profile Parameters:**
  - `temperature` — Controls randomness (0.0–2.0)
  - `max_tokens` — Output length limit
  - `reasoning_depth` — Chain-of-thought control
  - `speed_vs_accuracy` — Tradeoff preference
  - `cost_sensitivity` — Budget awareness
  - `multimodal` — Vision/image input enablement
  - `json_mode` — Strict schema enforcement
  - `tool_availability` — Function/tool calling enablement
- **Planned Built-in Profiles:**
  - **fast** — Low latency, low cost, minimal reasoning
  - **balanced** — General-purpose, stable outputs
  - **reasoning** — Deep chain-of-thought, higher accuracy
  - **vision** — Multimodal input/output
  - **json** — Strict JSON schema enforcement
  - **cheap** — Cost-optimized for high-volume batch tasks
- **Acceptance Criteria:**
  - Profiles produce consistent behavior when the underlying model changes.
  - Users can create custom profiles.
  - Profile parameters are validated against model capabilities (e.g., vision profile rejected if model lacks vision support).
  - ChatBuilder integrates with profiles via a `with_profile()` method.

#### Step 4: Prompt Template Selection
- **Description:** Templates define structure, tone, constraints, and formatting of outputs. Provider-agnostic and reusable.
- **Implementation:** YAML-based templates in `stratifyai/prompts/templates/` with a registry for discovery (`stratifyai/prompts/registry.py`).
- **Built-in Templates (10):**
  - `code_review.yaml`
  - `summarize.yaml`
  - `chatbot.yaml`
  - `explain_concept.yaml`
  - `analyze_data.yaml`
  - `rag_synthesis.yaml`
  - `translate.yaml`
  - `debug_error.yaml`
  - `commit_message.yaml`
  - `api_docs.yaml`
- **Acceptance Criteria:**
  - Templates work identically across all providers.
  - Users can add custom templates to `~/.stratifyai/prompts/`.
  - Template variables are validated before execution.
  - Templates are discoverable via CLI and API.

#### Step 5: User Input
- **Description:** User-supplied content fills template variables.
- **Supported Input Types:** Plain text, documents, images, JSON/CSV, multi-turn context.
- **Implementation:** Smart chunking (`stratifyai/chunking.py`), file extraction utilities (`stratifyai/utils/file_analyzer.py`, `csv_extractor.py`, `json_extractor.py`, `log_extractor.py`, `code_extractor.py`).
- **Acceptance Criteria:**
  - Large files are automatically chunked with configurable strategies.
  - File type is auto-detected and appropriate extractor is applied.
  - Image inputs are validated against model vision capability.
  - CSV/JSON schemas are extracted for structured analysis.

#### Step 6: Execution
- **Description:** StratifyAI assembles all pipeline components and executes the request.
- **Implementation:** `stratifyai/client.py` (LLMClient) with connection pooling, async-first design, and sync wrappers.
- **Capabilities:**
  - Streaming support across all providers (HTTP SSE + WebSocket)
  - Per-request cost tracking (`stratifyai/cost_tracker.py`)
  - Latency measurement on every response
  - Retry logic with exponential backoff and fallback models (`stratifyai/retry.py`)
  - Unified error handling with custom exception hierarchy (`stratifyai/exceptions.py`)
  - Response caching — in-memory and SQLite persistent (`stratifyai/caching.py`)
- **Acceptance Criteria:**
  - Streaming works for all 9 providers.
  - Failed requests retry with configurable attempts and fallback models.
  - Cost and latency are tracked on every request and exposed via API.
  - Cache hits return instant responses without API calls.

#### Step 7: Post-Processing (Partially Implemented)
- **Status:** Partially implemented. An active post-processing stage exists via middleware; a general-purpose pipeline is planned.
- **What exists today:**
  - `TrackedLLMClient._post_response()` — records cost entry, logs token/latency metadata, and updates the cost tracker after every non-streaming request. This is the primary post-processing stage today.
  - Budget enforcement pre-request via `_pre_request()` — blocks API calls when budget exceeded (HTTP 402)
  - Markdown rendering — client-side via `marked` + `highlight.js` in the Svelte frontend
  - Progressive summarization — standalone module (`stratifyai/summarization.py`), not wired into an automatic pipeline
- **Planned additions (Phase 9.5):**
  - JSON validation and schema enforcement on responses
  - Backend output normalization across providers
  - Structured field extraction pipeline
- **Acceptance Criteria:**
  - JSON-mode responses are validated against the requested schema.
  - Budget limits halt execution with clear messaging when exceeded (implemented).
  - Outputs are normalized to a consistent format regardless of provider.

---

### 4.2 Intelligent Routing
- **Implementation:** `stratifyai/router.py` with cost/quality/latency/hybrid strategies.
- **Acceptance Criteria:** capability filtering, fallback chains, audit logging.

### 4.3 RAG Pipeline
- **Implementation:** `stratifyai/rag.py` + `vectordb.py` + `embeddings.py`.
- **Acceptance Criteria:** ingest, embed, query, cite results.

### 4.4 Cost Tracking & Budget Enforcement
- **Implementation:** `stratifyai/cost_tracker.py` + `TrackedLLMClient`.
- **Acceptance Criteria:** per-request tracking, budget blocks, API/CLI stats.

### 4.5 ChatBuilder
- **Implementation:** `stratifyai/chat/builder.py`.
- **Acceptance Criteria:** immutable chaining, async + sync use.

### 4.6 Response Caching
- **Implementation:** `stratifyai/caching.py`.
- **Acceptance Criteria:** TTL, stats, CLI/API reporting.

---

## 5. Technical Stack (Summary)

**Backend:** Python 3.10+, FastAPI, uv, Pydantic, provider SDKs  
**Frontend:** Svelte 5, Vite, TypeScript, DOMPurify  
**Infra:** WebSockets, slowapi, ChromaDB, tiktoken  
**Testing:** pytest, ruff, black, mypy

---

## 6. Security & Compliance

- API keys via environment variables.  
- `STRATIFYAI_API_KEY` enforced for API.  
- Input validation and schema enforcement.  
- XSS protection for UI rendering.  

---

## 7. Roadmap & Phases

- Phases 1–8 complete (core, providers, routing, caching, RAG, UI, CLI, catalog).  
- **Phase 9: Profiles (Planned)**  
- **Phase 9.5: Post-Processing Enhancements (Planned)** — JSON schema validation, normalization, structured extraction  
- **Phase 10.1: MCP Server Core (Planned)**  
- **Phase 10.2: MCP Server Extended (Planned)**  
- **Phase 10.3: MCP Client (Deferred)**  
- Phase 11: Enterprise Hardening (multi-tenant, audit logging, SSO)

---

## 8. MCP Integration Plan (Full Inclusion)

### Executive Summary
MCP enables StratifyAI to be accessed by MCP-native clients (Claude Desktop, Cursor, Warp).  
Phases:  
- **10.1 Core Server**: tools + resources  
- **10.2 Extended**: RAG tools, prompt exposure, subscriptions  
- **10.3 Client**: deferred  

### MCP Primitives
- **Tools**: actions a client can invoke  
- **Resources**: read-only data via URIs  
- **Prompts**: reusable templates (exposed in Phase 9.3)

### Architecture Alignment
- MCP tools map to existing `TrackedLLMClient` and `Router`.
- MCP is mounted alongside FastAPI without changing existing endpoints.
- Auth reuses `STRATIFYAI_API_KEY`.

### Phase 10.1 (Core)
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

### Phase 10.2 (Extended)
- Tools: `rag_index`, `rag_query`, `analyze_file`, `route_for_extraction`, `get_cache_stats`
- Prompts: expose templates as MCP Prompts
- Subscriptions: cost summary updates

### Phase 10.3 (Deferred)
- MCP Client with tool execution loop
- Provider tool schema translation
- New orchestration engine

### Security Model
- Streamable HTTP protected by API key middleware  
- Stdio transport trusts local environment  
- Budget enforcement flows through `TrackedLLMClient`

### Testing Strategy
- Unit tests for tool handlers  
- Integration tests via MCP SDK client session  
- Validate resource responses and auth behavior

### Dependency Impact
- Add `mcp>=1.7.0`  
- Transitive deps: `starlette`, `httpx`, `anyio`, `sse-starlette`

### Risk Assessment
- SDK churn → pin dependency  
- Auth bypass → middleware  
- Costs → enforce budget tracking  

---

## 9. Success Metrics

- Profiles used in >60% of requests by day 90.  
- MCP server adopted by top MCP clients within 30 days.  
- Zero regressions in CLI/API workflows.  
- Reduction in configuration-related support requests.  

---

## 10. Open Questions

- Should profiles be opt-in or default?  
- Should profiles be versioned?  
- Should MCP tools accept profile parameters directly?  
