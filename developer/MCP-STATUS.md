# MCP Implementation Status Tracker

Last Updated: 2026-04-04
Project Board: https://github.com/users/Bytes0211/projects/4

## Status Definitions

- Planned: Not started yet.
- In Progress: Active implementation or validation work.
- Blocked: Waiting on dependency or decision.
- Done: Acceptance criteria met and merged.

## Reference Documents

| Document | Scope |
|----------|-------|
| `developer/PRD-MCP-implemenation.md` (v1.2) | MCP Server — StratifyAI exposes tools to external clients |
| `developer/MCP-IMPLEMENTATION-PLAN.md` | MCP Server — detailed execution plan with code patterns |
| `developer/PRD-MCP-abstraction-layer.md` | MCP Abstraction Layer — catalog, config wizard, inline tool tester |
| `developer/PRD-MCP-client-engine.md` | MCP Client Engine — StratifyAI spawns and calls external MCP servers |

---

## Workstream A: MCP Server

### Phase Tracking

| Phase | Scope | GitHub Issue | Status | PR | Updated | Notes |
|---|---|---|---|---|---|---|
| 0 | Contract Freeze | https://github.com/Bytes0211/stratifyai/issues/19 | Done | - | 2026-04-03 | Contract and plan docs finalized |
| 1 | Bootstrap | https://github.com/Bytes0211/stratifyai/issues/20 | Done | - | 2026-04-03 | MCP server scaffold, entrypoint, schemas, and errors verified |
| 2 | Core Tools | https://github.com/Bytes0211/stratifyai/issues/21 | Done | - | 2026-04-03 | Core MCP execution and model lookup tools verified in tools.py |
| 3 | Cost Tools | https://github.com/Bytes0211/stratifyai/issues/22 | Done | - | 2026-04-03 | Session cost tracking, summary filters, and validation tooling verified |
| 4 | Resources | https://github.com/Bytes0211/stratifyai/issues/23 | Done | - | 2026-04-03 | MCP resources verified with focused resource test coverage |
| 5 | Prompts | https://github.com/Bytes0211/stratifyai/issues/24 | Done | - | 2026-04-03 | Named and dynamic MCP prompts verified with prompt test coverage |
| 6 | HTTP Transport | https://github.com/Bytes0211/stratifyai/issues/25 | Planned | - | 2026-04-03 | Deferred post-GA |
| 7 | Tests and CI | https://github.com/Bytes0211/stratifyai/issues/26 | Done | - | 2026-04-03 | 75 MCP tests, 71%+ coverage, CI updated with --extra mcp |
| 8 | Docs and Config | https://github.com/Bytes0211/stratifyai/issues/27 | Done | - | 2026-04-03 | Quickstart, tools reference, client config docs written |
| 9 | Rollout and Verification | https://github.com/Bytes0211/stratifyai/issues/28 | Planned | - | 2026-04-03 | Phase field assigned in project |

### Step-Level Tracking

#### Phase 0 - Contract Freeze

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| P0-S1 | Freeze tool/resource/prompt contracts in PRD section 7 | Done | 2026-04-03 | developer/PRD-MCP-implemenation.md |
| P0-S2 | Freeze error model in PRD section 8 | Done | 2026-04-03 | developer/PRD-MCP-implemenation.md |
| P0-S3 | Finalize implementation plan with per-phase acceptance criteria | Done | 2026-04-03 | developer/MCP-IMPLEMENTATION-PLAN.md |

#### Phase 1 - Server Bootstrap

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| P1-S1 | Create mcp_server package scaffold and server composition | Done | 2026-04-03 | stratifyai/mcp_server/server.py |
| P1-S2 | Add CLI entrypoint and transport arg parsing | Done | 2026-04-03 | stratifyai/mcp_server/__main__.py |
| P1-S3 | Add schemas and structured error mapping modules | Done | 2026-04-03 | stratifyai/mcp_server/schemas.py; stratifyai/mcp_server/errors.py |
| P1-S4 | Add pyproject extras and package wiring for mcp | Done | 2026-04-03 | pyproject.toml |
| P1-S5 | Verify server boot and MCP handshake baseline | Done | 2026-04-03 | stratifyai/mcp_server/__init__.py |

#### Phase 2 - Core Tools

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| P2-S1 | Implement chat_completion tool with schema output | Done | 2026-04-03 | stratifyai/mcp_server/tools.py |
| P2-S2 | Implement chat_with_routing tool with route metadata | Done | 2026-04-03 | stratifyai/mcp_server/tools.py |
| P2-S3 | Implement list_providers and list_models tools | Done | 2026-04-03 | stratifyai/mcp_server/tools.py |
| P2-S4 | Implement get_model_info tool with catalog metadata | Done | 2026-04-03 | stratifyai/mcp_server/tools.py |
| P2-S5 | Validate structured errors for invalid provider/model | Done | 2026-04-03 | tests/test_mcp_tools.py |

#### Phase 3 - Cost and Validation Tools

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| P3-S1 | Add mcp session cost tracker wiring in tools module | Done | 2026-04-03 | stratifyai/mcp_server/tools.py |
| P3-S2 | Implement get_cost_summary tool and filters | Done | 2026-04-03 | stratifyai/mcp_server/tools.py |
| P3-S3 | Implement validate_provider tool | Done | 2026-04-03 | stratifyai/mcp_server/tools.py |
| P3-S4 | Implement estimate_cost tool using token counter | Done | 2026-04-03 | stratifyai/mcp_server/tools.py |
| P3-S5 | Verify cost totals update after chat tool calls | Done | 2026-04-03 | tests/test_mcp_tools.py |

#### Phase 4 - Resources

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| P4-S1 | Implement stratifyai://catalog resource | Done | 2026-04-03 | stratifyai/mcp_server/resources.py |
| P4-S2 | Implement stratifyai://catalog/{provider} resource | Done | 2026-04-03 | stratifyai/mcp_server/resources.py |
| P4-S3 | Implement providers and costs resources | Done | 2026-04-03 | stratifyai/mcp_server/resources.py |
| P4-S4 | Implement router strategies resource | Done | 2026-04-03 | stratifyai/mcp_server/resources.py |
| P4-S5 | Validate structured errors for unknown provider resource | Done | 2026-04-03 | tests/test_mcp_resources.py |

#### Phase 5 - Prompt Exposure

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| P5-S1 | Register compare_models prompt | Done | 2026-04-03 | stratifyai/mcp_server/prompts.py |
| P5-S2 | Register recommend_model prompt | Done | 2026-04-03 | stratifyai/mcp_server/prompts.py |
| P5-S3 | Register analyze_costs prompt | Done | 2026-04-03 | stratifyai/mcp_server/prompts.py |
| P5-S4 | Expose dynamic registry templates as prompts | Done | 2026-04-03 | stratifyai/mcp_server/prompts.py |
| P5-S5 | Validate prompt output shape (role/content list) | Done | 2026-04-03 | tests/test_mcp_prompts.py |

#### Phase 6 - HTTP Transport (Optional, Post-GA)

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| P6-S1 | Add streamable-http runtime flags (host/port) | Planned | 2026-04-03 | Issue 25 |
| P6-S2 | Add token/auth guidance for remote usage | Planned | 2026-04-03 | Issue 25 |
| P6-S3 | Add HTTP transport integration tests | Planned | 2026-04-03 | Issue 25 |

#### Phase 7 - Tests and CI

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| P7-S1 | Add test_mcp_schemas and error mapping tests | Done | 2026-04-03 | tests/test_mcp_schemas.py (35 tests) |
| P7-S2 | Add test_mcp_tools for core and cost tools | Done | 2026-04-03 | tests/test_mcp_tools.py (20 tests) |
| P7-S3 | Add test_mcp_resources and prompt tests | Done | 2026-04-03 | tests/test_mcp_resources.py (13 tests); tests/test_mcp_prompts.py (12 tests) |
| P7-S4 | Add optional integration test lane and marker handling | Planned | 2026-04-03 | Issue 26 |
| P7-S5 | Add CI gates for mcp extras, ruff, mypy, coverage | Done | 2026-04-03 | .github/workflows/ci.yml (--extra mcp added) |

#### Phase 8 - Docs and Client Setup

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| P8-S1 | Write MCP quickstart doc | Done | 2026-04-03 | docs/MCP-QUICKSTART.md |
| P8-S2 | Write MCP tools reference doc | Done | 2026-04-03 | docs/MCP-TOOLS-REFERENCE.md |
| P8-S3 | Write MCP client config doc | Done | 2026-04-03 | docs/MCP-CLIENT-CONFIG.md |
| P8-S4 | Add README links to MCP docs | Planned | 2026-04-03 | Issue 27 |
| P8-S5 | Validate setup path for at least two MCP clients | Planned | 2026-04-03 | Issue 27 |

#### Phase 9 - Rollout and Verification

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| P9-S1 | Run GA checklist and verify no P0/P1 defects | Planned | 2026-04-03 | Issue 28 |
| P9-S2 | Validate catalog resource output against schema | Planned | 2026-04-03 | Issue 28 |
| P9-S3 | Confirm integration in Claude Desktop and one additional client | Planned | 2026-04-03 | Issue 28 |
| P9-S4 | Add changelog entry and update project status docs | Planned | 2026-04-03 | Issue 28 |
| P9-S5 | Mark project board and status tracker complete | Planned | 2026-04-03 | Issue 28 |

---

## Workstream B: MCP Abstraction Layer

Reference: `developer/PRD-MCP-abstraction-layer.md`

### Phase Tracking

| Phase | Scope | GitHub Issue | Status | Updated | Notes |
|---|---|---|---|---|---|
| AL-1 | Catalog + CLI Core | https://github.com/Bytes0211/stratifyai/issues/33 | Done | 2026-04-03 | Catalog manager, CLI wizard, config generation for 4 clients, prerequisite validation verified |
| AL-2 | Additional CLI Commands | https://github.com/Bytes0211/stratifyai/issues/34 | Done | 2026-04-03 | `mcp status/add/add-custom/remove` implemented and verified with focused CLI tests |
| AL-3 | Web UI | https://github.com/Bytes0211/stratifyai/issues/35 | Done | 2026-04-03 | MCP API endpoints, Svelte management page, and preview/apply/export flow implemented and verified |
| AL-4 | Inline Tool Tester | https://github.com/Bytes0211/stratifyai/issues/36 | Done | 2026-04-03 | Test-tool API, tool browser with schemas, JSON execution panel, and saved presets implemented and verified |
| AL-5 | Polish | https://github.com/Bytes0211/stratifyai/issues/37 | Planned | 2026-04-03 | Health checks, custom server Web UI, tests and docs |

### Step-Level Tracking

#### AL Phase 1 - Catalog + CLI Core

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| AL1-S1 | Create mcp_catalog package with catalog.json | Done | 2026-04-03 | stratifyai/mcp_catalog/__init__.py; stratifyai/mcp_catalog/schemas.py; stratifyai/mcp_catalog/catalog.json (20 curated servers) |
| AL1-S2 | Implement catalog manager (load, search, validate) | Done | 2026-04-03 | stratifyai/mcp_catalog/manager.py (load_catalog, get_server, list_servers, validate_prerequisites) |
| AL1-S3 | Implement `stratifyai mcp list` command | Done | 2026-04-03 | cli/stratifyai_cli.py @mcp_app.command (mcp_list function) |
| AL1-S4 | Implement `stratifyai mcp setup` interactive wizard | Done | 2026-04-03 | cli/stratifyai_cli.py @mcp_app.command (mcp_setup function with --dry-run support) |
| AL1-S5 | Implement config generation for 4 clients (Claude Desktop, Claude Code, Cursor, VS Code) | Done | 2026-04-03 | stratifyai/mcp_catalog/manager.py (build_client_config, build_claude_code_commands) |
| AL1-S6 | Implement config file read/merge/write with backup | Done | 2026-04-03 | stratifyai/mcp_catalog/manager.py (write_client_config with automatic backup on existing files) |
| AL1-S7 | Implement prerequisite validation (Node.js, Docker) | Done | 2026-04-03 | stratifyai/mcp_catalog/manager.py (validate_prerequisites function) |
| AL1-S8 | Implement `stratifyai mcp catalog-update` (fetch from GitHub) | Done | 2026-04-03 | cli/stratifyai_cli.py @mcp_app.command (mcp_catalog_update function); stratifyai/mcp_catalog/manager.py (update_catalog) |

#### AL Phase 2 - Additional CLI Commands

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| AL2-S1 | Implement `stratifyai mcp status` | Done | 2026-04-03 | cli/stratifyai_cli.py (`mcp_status`); tests/test_mcp_catalog.py::test_mcp_status_shows_configured_servers |
| AL2-S2 | Implement `stratifyai mcp add <server>` | Done | 2026-04-03 | cli/stratifyai_cli.py (`mcp_add`); tests/test_mcp_catalog.py::test_mcp_add_writes_single_server |
| AL2-S3 | Implement `stratifyai mcp add-custom` | Done | 2026-04-03 | cli/stratifyai_cli.py (`mcp_add_custom`); tests/test_mcp_catalog.py::test_mcp_add_custom_writes_custom_server |
| AL2-S4 | Implement `stratifyai mcp remove <server>` | Done | 2026-04-03 | cli/stratifyai_cli.py (`mcp_remove`); stratifyai/mcp_catalog/manager.py (`remove_server_from_config`) |
| AL2-S5 | Implement `stratifyai mcp setup --dry-run` | Done | 2026-04-03 | cli/stratifyai_cli.py (`mcp_setup`); tests/test_mcp_catalog.py::test_mcp_setup_dry_run_outputs_cursor_config |

#### AL Phase 3 - Web UI

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| AL3-S1 | Add API endpoints (catalog, status, configure, clients) | Done | 2026-04-03 | api/main.py (`/api/mcp/catalog`, `/api/mcp/status`, `/api/mcp/configure`, `/api/mcp/clients`); tests/test_mcp_catalog.py API coverage |
| AL3-S2 | Build Svelte "MCP Servers" tab with catalog browser | Done | 2026-04-03 | frontend/src/lib/components/mcp/MCPServersPage.svelte; frontend/src/lib/components/layout/AppShell.svelte; frontend/src/lib/components/layout/Header.svelte |
| AL3-S3 | Implement context-aware Apply/Export logic | Done | 2026-04-03 | frontend/src/lib/components/mcp/MCPServersPage.svelte; frontend/src/lib/api/client.ts (`configureMcp`) |
| AL3-S4 | Implement config preview, clipboard copy, download | Done | 2026-04-03 | frontend/src/lib/components/mcp/MCPServersPage.svelte; verified by `cd frontend && npm run build` |

#### AL Phase 4 - Inline Tool Tester

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| AL4-S1 | Add POST /api/mcp/test-tool endpoint | Done | 2026-04-03 | api/main.py (`/api/mcp/test-tool`, `/api/mcp/tools`); tests/test_mcp_catalog.py::test_api_mcp_test_tool_executes_list_providers |
| AL4-S2 | Build tool browser with schema display | Done | 2026-04-03 | frontend/src/lib/components/mcp/MCPToolTester.svelte; frontend/src/lib/api/client.ts (`getMcpTools`) |
| AL4-S3 | Build JSON input editor with execute/response viewer | Done | 2026-04-03 | frontend/src/lib/components/mcp/MCPToolTester.svelte; verified by `pytest tests/test_mcp_catalog.py tests/test_cli_auth_error.py` |
| AL4-S4 | Implement request preset save/load | Done | 2026-04-03 | frontend/src/lib/components/mcp/MCPToolTester.svelte (localStorage-backed presets) |

---

## Workstream C: MCP Client Engine

Reference: `developer/PRD-MCP-client-engine.md`

### Phase Tracking

| Phase | Scope | GitHub Issue | Status | Updated | Notes |
|---|---|---|---|---|---|
| CE-1 | Client Engine Core | https://github.com/Bytes0211/stratifyai/issues/38 | Done | 2026-04-04 | MCPClientEngine core, ServerManager, stdio ClientSession wrapper, config loader, and E2E tool/resource test implemented |
| CE-2 | Tool Registry & Namespacing | https://github.com/Bytes0211/stratifyai/issues/39 | Done | 2026-04-04 | Namespaced ToolRegistry, per-server lifecycle registration, and verified start/stop/restart behavior |
| CE-3 | Chat Integration | https://github.com/Bytes0211/stratifyai/issues/40 | Done | 2026-04-04 | MCP-aware LLM chat loop, tool result injection, active server selection, and API/WebSocket chat integration verified |
| CE-4 | Permissions & Safety | https://github.com/Bytes0211/stratifyai/issues/41 | Done | 2026-04-04 | Permission manager, safety defaults, config-backed server toggles, and confirmation gating verified |
| CE-5 | Web UI Panels | https://github.com/Bytes0211/stratifyai/issues/42 | Done | 2026-04-04 | Live dashboard controls, tool discovery, chat badges, and permission manager shipped and verified |
| CE-6 | API & Diagnostics | https://github.com/Bytes0211/stratifyai/issues/43 | Done | 2026-04-04 | Tool execution/resource endpoints and health diagnostics verified |
| CE-7 | Tests & Documentation | https://github.com/Bytes0211/stratifyai/issues/44 | Planned | 2026-04-03 | Unit, integration, UI tests, user docs |

---

## Unified Execution Order

After completing the MCP Server (Workstream A, Phases 0-5 and 7-8), the remaining work was re-sequenced across Workstreams B and C to maximize value at each step and avoid building UI or tooling against surfaces that don't exist yet.

### Rationale

The original workstream layout treated the Abstraction Layer and Client Engine as independent tracks. In practice they share a dependency chain: the Client Engine needs the catalog and config layer to know what to spawn, and the Web UI is far more useful when it can show live engine state rather than just export static config files. Permissions must also land before tool calling is exposed in any UI.

The re-ordered sequence interleaves the two workstreams so that each phase builds on the last and nothing is built speculatively.

### Execution Sequence

| Order | Phase | Scope | Rationale |
|-------|-------|-------|-----------|
| 1 | AL-1 | Catalog + CLI Core | Foundation. Everything downstream reads from the catalog and user config. |
| 2 | AL-2 | Additional CLI Commands | Small scope. Gives users `add/remove/status` to manage config before the engine exists. Tests catalog without engine. |
| 3 | CE-1 | Client Engine Core | Big piece. Spawns servers, performs handshake, calls tools. Depends on catalog from AL-1. |
| 4 | CE-2 | Tool Registry & Namespacing | Natural continuation of CE-1. Spawning servers without an aggregated tool list is unusable. |
| 5 | AL-3 | Web UI | Built after engine exists, so it can show live server status and tool counts — not just a config exporter. |
| 6 | CE-3 | Chat Integration | Wires the engine into the chat flow. LLM can now call MCP tools during conversation. |
| 7 | CE-4 | Permissions & Safety | Must land before tool calling is exposed in any user-facing UI. |
| 8 | AL-4 | Inline Tool Tester | Now tests both StratifyAI's own tools and tools from external servers via the engine. |
| 9 | CE-5 | Web UI Panels | Server dashboard, tool discovery, chat badges. Builds on AL-3 components and CE-4 permissions. |
| 10 | CE-6 | API & Diagnostics | REST endpoints, health monitoring. Polish layer. |
| 11 | AL-5 + CE-7 | Polish + Tests | Final quality pass across both workstreams. |

### Deferred

| Phase | Scope | Status | Reason |
|-------|-------|--------|--------|
| Server Phase 6 | HTTP Transport | Deferred post-GA | stdio covers primary use case; HTTP adds complexity with auth requirements |
| Server Phase 9 | Rollout & Verification | Deferred | Execute after Client Engine proves the full stack end-to-end |

### Step-Level Tracking (Execution Order)

Steps are listed in the same interleaved sequence as the execution order above. AL step-level tracking is in Workstream B above; these are the remaining CE and combined steps.

#### Step 3: CE-1 — Client Engine Core

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| CE1-S1 | Implement `MCPClientEngine` orchestrator (start, stop, call_tool, get_resource, list_tools, list_servers) | Done | 2026-04-04 | stratifyai/mcp_client/engine.py |
| CE1-S2 | Implement `ServerManager` — spawn/stop/restart stdio subprocesses via `asyncio.create_subprocess_exec` | Done | 2026-04-04 | stratifyai/mcp_client/server_manager.py |
| CE1-S3 | Implement `connection.py` — `ClientSession` wrapper with reconnect and timeout logic | Done | 2026-04-04 | stratifyai/mcp_client/connection.py |
| CE1-S4 | Implement `config.py` — load enabled servers from catalog + user config | Done | 2026-04-04 | stratifyai/mcp_client/config.py |
| CE1-S5 | End-to-end test: spawn a real MCP server (e.g. filesystem), call a tool, verify result | Done | 2026-04-04 | tests/test_mcp_client_engine.py::test_mcp_client_engine_start_call_tool_and_get_resource |

#### Step 4: CE-2 — Tool Registry & Namespacing

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| CE2-S1 | Implement `ToolRegistry` with register/unregister per server | Done | 2026-04-04 | stratifyai/mcp_client/tool_registry.py (`register_server_tools`, `unregister_server`, `list_server_tools`) |
| CE2-S2 | Namespace tools as `{server_id}.{tool_name}` to prevent collisions | Done | 2026-04-04 | stratifyai/mcp_client/tool_registry.py (`namespace=f"{server_id}.{tool_name}"`) |
| CE2-S3 | Handle server connect/disconnect events (auto register/unregister) | Done | 2026-04-04 | stratifyai/mcp_client/engine.py (`start_server`, `stop_server`, `restart_server`) |
| CE2-S4 | Implement `list_all()` returning merged tool list across all servers | Done | 2026-04-04 | stratifyai/mcp_client/tool_registry.py (`list_all()`); verified by `uv run pytest tests/test_mcp_client_engine.py` |
| CE2-S5 | Implement `find_tool(server, name)` lookup | Done | 2026-04-04 | stratifyai/mcp_client/tool_registry.py (`find_tool`, `find_by_namespace`); verified by `uv run pytest tests/test_mcp_client_engine.py` |

#### Step 5: AL-3 — Web UI

See Workstream B step-level tracking above.

#### Step 6: CE-3 — Chat Integration

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| CE3-S1 | Inject tool definitions from registry into LLM tool_use parameter | Done | 2026-04-04 | stratifyai/mcp_client/engine.py (`build_tool_definitions`, provider-specific formatting for OpenAI/Anthropic) |
| CE3-S2 | Intercept LLM tool_use requests and route through MCPClientEngine | Done | 2026-04-04 | stratifyai/mcp_client/engine.py (`chat_with_mcp`, `_extract_tool_requests`, `_execute_tool_requests`) |
| CE3-S3 | Inject tool results back into conversation context | Done | 2026-04-04 | stratifyai/mcp_client/engine.py (`_build_followup_messages`); tests/test_mcp_client_engine.py::test_mcp_client_engine_chat_with_mcp_executes_tool_calls |
| CE3-S4 | Implement active server selection per chat session | Done | 2026-04-04 | api/main.py (`active_mcp_servers` in REST/WebSocket request path); stratifyai/client.py (`chat_with_mcp`) |
| CE3-S5 | Implement fallback behavior when server is offline (warn + exclude tools) | Done | 2026-04-04 | stratifyai/mcp_client/engine.py (`build_tool_definitions` warnings); tests/test_mcp_client_engine.py::test_mcp_client_engine_build_tool_definitions_filters_active_servers |

#### Step 7: CE-4 — Permissions & Safety

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| CE4-S1 | Implement `permissions.py` with allow/deny/confirm rule evaluation | Done | 2026-04-04 | `stratifyai/mcp_client/permissions.py`; `tests/test_mcp_client_engine.py::test_permission_manager_applies_safety_defaults_and_overrides` |
| CE4-S2 | Implement safety defaults: auto-allow read-only, confirm-before-execute for write tools | Done | 2026-04-04 | `stratifyai/mcp_client/engine.py` permission filtering + confirmation gating; destructive tools hidden unless approved |
| CE4-S3 | Implement per-server enable/disable and auto-start toggles | Done | 2026-04-04 | `stratifyai/mcp_client/config.py`; `cli/stratifyai_cli.py` (`--enabled/--disabled`, `--auto-start/--manual-start`) |
| CE4-S4 | Implement confirm-before-execute flow in CLI (prompt user before destructive tool calls) | Done | 2026-04-04 | Confirmation-aware engine hook exposed via `tool_confirmation_handler`; verified by `tests/test_mcp_client_engine.py::test_mcp_client_engine_confirmation_handler_can_approve_tool` |
| CE4-S5 | Load/save permission config from user config file | Done | 2026-04-04 | `stratifyai/mcp_catalog/manager.py` (`get_mcp_client_settings`, `write_mcp_client_settings`); `tests/test_mcp_catalog.py::test_write_mcp_client_settings_persists_permissions_metadata` |

#### Step 8: AL-4 — Inline Tool Tester

See Workstream B step-level tracking above.

#### Step 9: CE-5 — Web UI Panels

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| CE5-S1 | Build Server Dashboard — status cards with Start/Stop/Restart actions | Done | 2026-04-04 | `frontend/src/lib/components/mcp/MCPServersPage.svelte`; `/api/mcp-client/servers`; `/api/mcp-client/servers/{id}/start|stop|restart` |
| CE5-S2 | Build Tool Discovery Panel — browse tools per server, view schemas, test inline | Done | 2026-04-04 | `frontend/src/lib/components/mcp/MCPServersPage.svelte` live tool browser; `/api/mcp-client/tools`; inline tester retained via `MCPToolTester.svelte` |
| CE5-S3 | Build chat integration badges — show which server/tool was used per response | Done | 2026-04-04 | `frontend/src/lib/components/chat/ChatMessage.svelte`; `chat.ts`; `ChatInput.svelte`; `MCPChatSettings.svelte` |
| CE5-S4 | Build Permission Manager — table with allow/deny/confirm per tool, bulk actions | Done | 2026-04-04 | `frontend/src/lib/components/mcp/MCPServersPage.svelte`; `/api/mcp-client/permissions`; config-backed CE-4 rules surfaced in UI |

#### Step 10: CE-6 — API & Diagnostics

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| CE6-S1 | Implement `GET /api/mcp-client/servers` and `/servers/{id}/start\|stop\|restart` | Done | 2026-04-04 | `api/main.py` (`/api/mcp-client/servers*`); `tests/test_mcp_catalog.py::test_api_mcp_client_servers_and_tools_return_runtime_metadata` |
| CE6-S2 | Implement `GET /api/mcp-client/tools` and `POST /tools/{server}/{tool}` (execute) | Done | 2026-04-04 | `api/main.py` (`/api/mcp-client/tools`, `/api/mcp-client/tools/{server}/{tool}`, `/api/mcp-client/resources/{server}/{uri}`); `tests/test_mcp_catalog.py::test_api_mcp_client_tool_execution_and_resource_fetch` |
| CE6-S3 | Implement `GET/PUT /api/mcp-client/permissions` | Done | 2026-04-04 | `api/main.py` (`/api/mcp-client/permissions`); `tests/test_mcp_catalog.py::test_api_mcp_client_permissions_can_be_updated` |
| CE6-S4 | Implement `GET /api/mcp-client/health` with periodic ping and error reporting | Done | 2026-04-04 | `stratifyai/mcp_client/engine.py`; `stratifyai/mcp_client/server_manager.py`; `tests/test_mcp_catalog.py::test_api_mcp_client_health_reports_diagnostics` |

#### Step 11: AL-5 + CE-7 — Polish + Tests

AL-5 steps: see Workstream B step-level tracking above.

| Step ID | Step | Status | Updated | Evidence |
|---|---|---|---|---|
| CE7-S1 | Unit tests for engine, server manager, connection, tool registry, executor | Planned | 2026-04-04 | - |
| CE7-S2 | Unit tests for permissions (allow/deny/confirm rules, safety defaults) | Planned | 2026-04-04 | - |
| CE7-S3 | Integration test: spawn real MCP server (filesystem), call tool, verify end-to-end | Planned | 2026-04-04 | - |
| CE7-S4 | Web UI component tests for dashboard, tool discovery, permission manager | Planned | 2026-04-04 | - |
| CE7-S5 | User documentation and troubleshooting guide | Planned | 2026-04-04 | - |

---

## Update Workflow

1. Update issue status and checklist in GitHub first.
2. Update Step-Level Tracking entries for the active phase.
3. Roll up step progress to phase status in Phase Tracking.
4. Add PR link once opened.
5. Set phase status to Done only after merge and acceptance validation.
