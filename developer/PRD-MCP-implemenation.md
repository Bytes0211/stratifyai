# Technical Approach: StratifyAI MCP Server Implementation

Version: 1.1  
Date: 2026-04-02  
Owner: StratifyAI Core Team  
Status: Implementation Blueprint

---

## 1. Architecture Intent

Implement a production-ready Model Context Protocol (MCP) server for StratifyAI so MCP clients (Claude Desktop, Cursor, Claude Code, VS Code, Warp, Windsurf) can invoke StratifyAI capabilities through standardized tool/resource/prompt primitives.

This technical approach will:
- Expose multi-provider chat and routing via MCP tools.
- Expose catalog, provider health, and cost context via MCP resources.
- Expose reusable prompt templates via MCP prompts.
- Reuse existing StratifyAI core logic (`LLMClient`, `Router`, `CostTracker`, catalog manager, prompts registry) to avoid business-logic duplication.

---

## 2. Design Constraints and Non-Goals

### 2.1 Engineering Goals

- Deliver MCP server core with stdio transport first, then optional HTTP transport.
- Expose high-value tools for chat, routing, model lookup, validation, and cost insight.
- Provide stable typed schemas and predictable error behavior.
- Achieve test coverage across unit, contract, and integration layers.
- Provide clear client setup docs and examples.

### 2.2 Non-Goals (Initial Delivery)

- Multi-tenant auth framework for remote hosted MCP.
- OAuth 2.1 in initial release.
- Custom MCP client runtime/orchestration loop.
- Long-lived workflow state engine in MCP layer.

---

## 3. Current-State Gaps

StratifyAI currently offers CLI, API, and library interfaces, but no MCP server surface. Teams using MCP-native assistants cannot directly leverage StratifyAI model routing, unified provider abstraction, and cost controls.

Resulting gaps:
- No MCP-native interoperability.
- No standardized tool/resource/prompt exposure for assistants.
- No direct path for MCP clients to invoke routing and cost-aware operations.

---

## 4. Technical Objectives and SLO Targets

### 4.1 Contract and Protocol Objectives

- MCP clients can discover and call StratifyAI tools with valid schemas.
- MCP resources return consistent machine-readable context payloads.
- Prompt templates are discoverable via MCP prompt primitives.

### 4.2 Build and Quality Objectives

- 100% of planned phase acceptance criteria met.
- Unit and integration tests pass in CI.
- No regressions in existing CLI/API/tests.

### 4.3 Runtime Objectives

- Setup for Claude Desktop and Claude Code verified end-to-end.
- Clear error messages for invalid provider/model/auth conditions.
- p95 latency overhead from MCP wrapper < 150ms above equivalent direct call for non-streaming paths.

---

## 5. System Boundaries

### 5.1 In Scope

- New `stratifyai/mcp_server/` package.
- MCP tools, resources, and prompts.
- Optional dependency wiring in `pyproject.toml`.
- CLI/script entrypoint for MCP server.
- Documentation + client configuration examples.
- Unit/integration test coverage.

### 5.2 Out of Scope

- Hosted MCP gateway service.
- Account-level user management.
- Persistent MCP session store beyond existing app state.

---

## 6. Target Architecture

### 6.1 Package Layout

```text
stratifyai/
  mcp_server/
    __init__.py
    __main__.py
    server.py
    tools.py
    resources.py
    prompts.py
    schemas.py
    errors.py
```

### 6.2 Design Principles

- Thin wrapper layer around existing StratifyAI core modules.
- No duplicated routing/cost/provider logic.
- Strong schema contracts for MCP requests/responses.
- Centralized error mapping and sanitization.

### 6.3 Core Mappings

- `chat_completion` tool -> `LLMClient.chat_completion()`
- `chat_with_routing` tool -> `Router.route()` + `LLMClient.chat_completion()`
- `list_models`/`get_model_info` -> catalog manager/config
- `get_cost_summary` -> `CostTracker.get_summary()`
- Prompt exposure -> prompts registry templates

---

## 7. Interface Contracts

### 7.1 MCP Tools (Initial)

1. `chat_completion`
- Inputs: provider, model, messages[], temperature?, max_tokens?, stream?
- Output: content, provider, model, usage tokens, cost, latency metadata

2. `chat_with_routing`
- Inputs: messages[], strategy?, capabilities?[], max_cost?, max_latency?
- Output: selected provider/model + response + usage/cost

3. `list_providers`
- Inputs: none
- Output: provider names + configured/available status

4. `list_models`
- Inputs: provider
- Output: model IDs + key metadata (cost/context/capabilities)

5. `get_model_info`
- Inputs: provider, model
- Output: full metadata for model

6. `validate_provider`
- Inputs: provider
- Output: auth/config readiness + model availability snapshot

7. `get_cost_summary`
- Inputs: provider?, model?
- Output: summary totals + breakdowns

8. `estimate_cost`
- Inputs: provider, model, message_text
- Output: estimated tokens + projected cost

### 7.2 MCP Resources (Initial)

- `stratifyai://catalog`
- `stratifyai://catalog/{provider}`
- `stratifyai://providers`
- `stratifyai://costs`
- `stratifyai://router/strategies`

### 7.3 MCP Prompts (Initial)

- `compare_models(models[])`
- `recommend_model(task_description, budget?, priority?)`
- `analyze_costs(time_period?)`

---

## 8. Error, Security, and Reliability Model

### 8.1 Error Contract

Every tool failure returns structured error fields:
- error_code
- error_type
- message (sanitized)
- provider/model context when applicable

### 8.2 Security Requirements

- Reuse existing sanitizer behavior to avoid key/token leakage.
- Never echo raw API keys in MCP tool errors.
- Preserve existing auth semantics from provider clients.
- Validate all inbound MCP payload fields before executing core calls.

### 8.3 Reliability Requirements

- Timeouts must propagate from provider/client configuration.
- Retry behavior should stay in existing retry layer (no duplicate retry in MCP wrapper unless explicitly needed).

---

## 9. Packaging and Runtime

Update `pyproject.toml`:
- Add optional dependency group `mcp` with `mcp[cli]` minimum supported version.
- Extend `all` extras to include `mcp`.
- Add script entrypoint:
  - `stratifyai-mcp = "stratifyai.mcp_server.__main__:main"`

---

## 10. Detailed Implementation Plan

### Phase 0: Discovery and Contract Freeze

Objective:
- Finalize MCP primitive contracts, naming, and payload schemas.

Steps:
1. Confirm tool/resource/prompt list and argument names.
2. Align return shapes with existing API models where possible.
3. Define error code mapping table for common failure classes.
4. Freeze schema version `mcp_schema_version = 1`.

Deliverables:
- Contract spec section approved.
- `schemas.py` design finalized.

Acceptance Criteria:
- Team sign-off on names/inputs/outputs.
- No unresolved schema ambiguity.

---

### Phase 1: Server Bootstrap and Entry Points

Objective:
- Create runnable MCP server scaffold with stdio transport.

Steps:
1. Add `stratifyai/mcp_server/` package structure.
2. Implement `server.py` with FastMCP app initialization.
3. Implement `__main__.py` main() runner.
4. Add package exports in `__init__.py`.
5. Add dependency and script wiring in `pyproject.toml`.

Deliverables:
- `stratifyai-mcp` command starts server.
- Server can be discovered by MCP clients.

Acceptance Criteria:
- Local manual run starts cleanly.
- Claude Desktop test config can connect.

---

### Phase 2: Core Tool Set (Execution Path)

Objective:
- Deliver highest-value execution tools.

Steps:
1. Implement `chat_completion` tool wrapper.
2. Implement `chat_with_routing` tool wrapper.
3. Implement `list_providers` and `list_models` wrappers.
4. Implement `get_model_info` wrapper.
5. Map exceptions to structured MCP-friendly error payloads.
6. Add request validation with explicit field checks.

Deliverables:
- Working tool suite for basic query and routed query.

Acceptance Criteria:
- Tools return expected shape and metadata.
- Invalid provider/model returns structured errors.
- Existing cost tracking updates correctly for executed calls.

---

### Phase 3: Cost and Validation Tooling

Objective:
- Expose financial and readiness observability.

Steps:
1. Implement `get_cost_summary` tool.
2. Implement `validate_provider` tool.
3. Implement `estimate_cost` tool using token/cost utilities.
4. Add filtering options where applicable (provider/model scope).

Deliverables:
- Cost and readiness tools available to MCP clients.

Acceptance Criteria:
- Cost numbers align with existing API/CLI summaries.
- Validation reflects key/config state accurately.

---

### Phase 4: Resource Layer

Objective:
- Publish contextual data through MCP resources.

Steps:
1. Implement catalog resources (`catalog`, `catalog/{provider}`).
2. Implement providers status resource.
3. Implement cost summary resource.
4. Implement router strategies resource.
5. Ensure response payloads are stable and versioned.

Deliverables:
- Resource endpoints discoverable and consumable by MCP clients.

Acceptance Criteria:
- Resource fetches are deterministic and validated.
- Resource schema docs included.

---

### Phase 5: Prompt Exposure

Objective:
- Register prompt templates as MCP prompts.

Steps:
1. Integrate prompts registry.
2. Implement `compare_models`, `recommend_model`, `analyze_costs` prompts.
3. Add argument validation/default handling.
4. Ensure returned prompt messages use role/content schema expected by MCP.

Deliverables:
- Prompt primitives available and callable from MCP clients.

Acceptance Criteria:
- Prompts discoverable in MCP inspector/client.
- Prompt outputs are usable in follow-up tool calls.

---

### Phase 6: Transport Expansion (Optional for v1)

Objective:
- Add Streamable HTTP transport for remote integration scenarios.

Steps:
1. Add transport abstraction in server bootstrap.
2. Implement HTTP transport startup mode.
3. Add runtime flags/env for transport selection.
4. Add local auth guard guidance for non-stdio modes.

Deliverables:
- Optional remote transport runtime.

Acceptance Criteria:
- Both stdio and HTTP modes pass integration tests.

---

### Phase 7: Test Strategy and Quality Gates

Objective:
- Ensure robust behavior and low regression risk.

Test Layers:
1. Unit tests
- tools/resource/prompt functions with mocked `LLMClient`, `Router`, `CostTracker`.

2. Contract tests
- schema validation for inputs/outputs and error payloads.

3. Integration tests
- MCP Inspector + SDK client session tests for discovery and invocation.

4. Regression checks
- Existing project test suite remains green.

CI Gates:
- Ruff, Mypy, pytest (including MCP tests)
- Coverage threshold for new MCP package

Acceptance Criteria:
- All MCP tests pass in CI.
- No regressions in existing test suites.

---

### Phase 8: Documentation and Client Onboarding

Objective:
- Make adoption straightforward for users and contributors.

Steps:
1. Add MCP quickstart doc under docs.
2. Provide Claude Desktop and Claude Code config examples.
3. Document each tool/resource/prompt with examples.
4. Add troubleshooting section (common auth/config/client issues).
5. Add runbook entry and link from README/CONTRIBUTING.

Deliverables:
- End-user and contributor docs complete.

Acceptance Criteria:
- New contributor can configure MCP and execute first tool call in <= 15 minutes.

---

### Phase 9: Rollout Plan

### 9.1 Internal Beta

- Enable for core maintainers.
- Validate behavior across two MCP clients minimum.
- Track defects by category: schema, transport, provider, auth, docs.

### 9.2 Public Beta

- Publish documentation and examples.
- Gather user feedback for missing tools/resources.
- Prioritize critical defects and schema adjustments.

### 9.3 GA Criteria

- Zero P0/P1 defects open.
- Stable schema and backward compatibility notes published.
- CI and release process includes MCP tests by default.

---

## 11. Risks and Mitigations

1. MCP SDK/API evolution risk
- Mitigation: isolate SDK-specific glue in `server.py`; avoid leaking SDK types into core modules.

2. Tool schema drift risk
- Mitigation: contract tests + schema versioning.

3. Error leakage risk
- Mitigation: centralized sanitizer in MCP error mapping.

4. Performance overhead risk
- Mitigation: thin wrappers + existing connection pooling/client reuse.

---

## 12. Open Questions

1. Should MCP tool responses include optional raw provider payloads behind a debug flag?
2. Should `chat_with_routing` support strict provider allow/deny lists in v1?
3. Should Streamable HTTP be included in initial GA or remain post-GA extension?
4. Should prompt exposure include all templates automatically or only an approved subset?

---

## 13. Post-GA Expansion

- MCP sampling support.
- OAuth 2.1 for hosted/remote deployment mode.
- Subscription-like notifications for cost threshold events.
- Team-scoped policy enforcement (provider/model allowlists).
- MCP client orchestration loop (deferred).
