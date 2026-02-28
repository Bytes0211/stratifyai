---
title: "Phase 9.1: Prompt Template System"
labels: ["enhancement", "templates", "dx", "production"]
milestone: "Phase 9 - Advanced Features"
assignees: []
---

## Phase 9.1 — Prompt Template System

**Priority:** 💡 HIGH — Developer experience & common task patterns
**Estimated effort:** 2–3 days
**Branch:** `feat/phase-9.1-prompt-templates`
**Status:** ✅ COMPLETE (Feb 27, 2026)

### Context

StratifyAI has no prompt template infrastructure. System prompts and user prompt patterns are hardcoded inline across example scripts, the CLI, and the API. This creates duplication, no discoverability, and no reusability across projects.

This phase introduces a lightweight, type-safe prompt template system with 10 built-in templates, full API/CLI/ChatBuilder integration, and user extensibility.

### References

- **Plan:** `docs/PROMPT-TEMPLATES-PLAN.md`
- **Documentation:** `docs/PROMPT-TEMPLATES.md`
- **Developer Journal:** `docs/developer-journal.md` — Feb 27, 2026 entry

---

### Task List

#### 9.1.1 — PromptTemplate Data Model
> **File:** `stratifyai/prompts/models.py`

- [x] Create `PromptParameter` dataclass with validation (string, text, number, choice types)
- [x] Create `PromptTemplate` dataclass with `render(**kwargs) -> list[Message]` method
- [x] Use `str.format_map()` for safe parameter substitution (no eval/exec)
- [x] Add `to_dict()` method for API serialization
- [x] Support `default` values and `required` flag on parameters
- [x] Support `choices` list for choice-type parameters
- [x] Validate parameters before rendering, raise clear ValueError messages
- [x] Warn on unknown parameters (typos)

**Why:** Templates need type-safe parameter validation and secure rendering without code execution risk.

**Validation:**
```bash
pytest tests/test_prompts.py::test_prompt_parameter_validate_required -v
pytest tests/test_prompts.py::test_prompt_template_render_basic -v
```

---

#### 9.1.2 — Built-in Template Library
> **Directory:** `stratifyai/prompts/templates/`

- [x] Create 10 YAML templates (~50–80 lines each):
  - [x] `code_review.yaml` — Code review for bugs, security, performance
  - [x] `summarize.yaml` — Document summarization with configurable style
  - [x] `chatbot.yaml` — Conversational assistant with persona
  - [x] `explain_concept.yaml` — Explain complex concepts at different levels
  - [x] `analyze_data.yaml` — Analyze CSV, JSON, tabular data
  - [x] `rag_synthesis.yaml` — Synthesize answers from retrieved context
  - [x] `translate.yaml` — Language translation with formality control
  - [x] `debug_error.yaml` — Debug error messages and stack traces
  - [x] `commit_message.yaml` — Generate conventional commit messages
  - [x] `api_docs.yaml` — Generate API documentation from code
- [x] Each template includes: name, description, tags, parameters, system prompt, user prompt
- [x] Add `recommended_models` and `recommended_temperature` fields
- [x] Use sensible defaults to minimize required parameters

**Why:** Provides reusable, production-ready templates for common AI tasks.

**Validation:**
```bash
pytest tests/test_prompts.py::test_all_builtin_templates_render_with_defaults -v
```

---

#### 9.1.3 — PromptRegistry (Discovery & Loading)
> **File:** `stratifyai/prompts/registry.py`

- [x] Create singleton `PromptRegistry` class with lazy loading
- [x] Implement `get(name: str) -> PromptTemplate` with helpful error messages
- [x] Implement `list(tag=None, source=None) -> list[PromptTemplate]` with filtering
- [x] Implement `render(name, **kwargs) -> list[Message]` shortcut
- [x] Implement `search(query: str) -> list[PromptTemplate]` for name/description/tags
- [x] Implement `tags() -> list[str]` for unique tag list
- [x] Implement `load_directory(path, source)` for YAML discovery
- [x] Load built-in templates from `stratifyai/prompts/templates/`
- [x] Load user templates from `~/.stratifyai/prompts/` (if exists)
- [x] User templates with same name override built-in templates
- [x] Use `yaml.safe_load()` exclusively (no `yaml.load()`)

**Why:** Centralized discovery and loading with user extensibility.

**Validation:**
```bash
pytest tests/test_prompts.py::test_registry_loads_builtin_templates -v
pytest tests/test_prompts.py::test_registry_user_overrides_builtin -v
```

---

#### 9.1.4 — ChatBuilder Integration
> **File:** `stratifyai/chat/builder.py`

- [x] Add `with_template(name: str, **params) -> ChatBuilder` method
- [x] Load template from registry and render with parameters
- [x] Apply rendered system prompt to builder's `_system` field
- [x] Store rendered user prompt in new `_template_user` field
- [x] Auto-apply `recommended_temperature` if builder has no temperature set
- [x] Update `_clone()` to include `_template_user` field
- [x] Update `_build_messages()` to prepend template user message
- [x] Allow explicit user prompt to be appended after template user message

**Why:** Seamless integration with existing fluent API.

**Validation:**
```bash
pytest tests/test_prompts.py::test_chatbuilder_integration -v
```

---

#### 9.1.5 — CLI Integration
> **File:** `cli/stratifyai_cli.py`

- [x] Create new `templates` command:
  - [x] List all templates with `--tag` filter
  - [x] Show detailed parameters with `--verbose` flag
  - [x] Display Rich table with name, description, tags, source
- [x] Add `--template` option to `chat` command
- [x] Add `--params` option to `chat` command (comma-separated key=value pairs)
- [x] Parse params string into dictionary
- [x] If `--file` provided, inject as first required text parameter
- [x] Render template and use resulting messages
- [x] Show "✓ Applied template: {name}" confirmation

**Why:** Makes templates easily accessible from the command line.

**Validation:**
```bash
stratifyai templates
stratifyai templates --tag code --verbose
stratifyai chat --template summarize --params "style=bullet_points" --file test.txt
```

---

#### 9.1.6 — API Integration
> **File:** `api/main.py`

- [x] Create `GET /api/templates` endpoint:
  - [x] Support `?tag=` and `?source=` query params
  - [x] Return list of template metadata via `to_dict()`
- [x] Create `GET /api/templates/{name}` endpoint:
  - [x] Return single template metadata
  - [x] Return 404 with available templates list if not found
- [x] Create `POST /api/templates/{name}/render` endpoint:
  - [x] Accept `{"params": {...}}` JSON body
  - [x] Render template and return `list[{"role": "...", "content": "..."}]`
  - [x] Return 422 for invalid parameters with validation error
- [x] Add `TemplateRenderRequest` Pydantic model

**Why:** REST API access for web UI and external integrations.

**Validation:**
```bash
curl http://localhost:8080/api/templates
curl http://localhost:8080/api/templates/code_review
curl -X POST http://localhost:8080/api/templates/code_review/render \
  -H "Content-Type: application/json" \
  -d '{"params": {"code": "x=1", "language": "python"}}'
```

---

#### 9.1.7 — MCP Prompt Exposure
> **File:** `stratifyai/mcp_server.py`
> **Status:** ⏳ DEFERRED to Phase 9.2 (MCP Server Core)

- [ ] Register all templates as MCP Prompts when MCP server exists
- [ ] Dynamic registration with parameter schemas
- [ ] Handle parameter type conversion for MCP protocol

**Why:** MCP clients (Claude Desktop, Cursor) can discover and use templates.

**Deferred:** Requires Phase 9.2 MCP server infrastructure first.

---

#### 9.1.8 — User-Defined Templates
> **Directory:** `~/.stratifyai/prompts/`

- [x] Document YAML schema in `docs/PROMPT-TEMPLATES.md`
- [x] Registry automatically discovers user templates on first access
- [x] User templates override built-in templates with same name
- [x] `source` field tracks "builtin" vs "user" provenance
- [x] Templates validate on load (warn on errors, don't crash)

**Why:** Teams can create project-specific templates without modifying library.

**Validation:**
```bash
# Create ~/.stratifyai/prompts/custom.yaml
# Run: stratifyai templates
# Verify custom template appears with source=user
```

---

#### 9.1.9 — Tests
> **File:** `tests/test_prompts.py`

- [x] 30 comprehensive tests covering:
  - [x] Parameter validation (required, defaults, choices, number coercion)
  - [x] Template rendering (basic, with defaults, missing params, unknown params)
  - [x] Template serialization (`to_dict()`)
  - [x] Registry operations (get, list, search, tags, register)
  - [x] YAML loading (valid, minimal, invalid)
  - [x] User directory loading and override behavior
  - [x] Integration with `ChatRequest` and `ChatBuilder`
  - [x] Built-in template rendering with real parameters
- [x] All tests passing (100%)

**Validation:**
```bash
pytest tests/test_prompts.py -v
# Expected: 30 passed
```

---

#### 9.1.10 — Documentation
> **Files:** `docs/PROMPT-TEMPLATES.md`, `AGENTS.md`, `README.md`, `ENTERPRISE_README.md`, `docs/GETTING-STARTED.md`, `docs/developer-journal.md`

- [x] Create complete user guide in `docs/PROMPT-TEMPLATES.md`:
  - [x] Quick start examples
  - [x] Built-in templates table
  - [x] Usage with ChatBuilder, CLI, API
  - [x] Custom template creation guide
  - [x] Template YAML schema reference
  - [x] Security notes (str.format_map, yaml.safe_load)
  - [x] Best practices
  - [x] Troubleshooting
- [x] Update `AGENTS.md`:
  - [x] Add `stratifyai/prompts/` to project structure
  - [x] Add `tests/test_prompts.py` to test list
  - [x] Update test count (408+)
  - [x] Mark Phase 9.1 as complete
  - [x] Add to documentation list
- [x] Update `README.md`:
  - [x] Add prompt templates to features list
  - [x] Add usage example section
  - [x] Update status badge
- [x] Update `ENTERPRISE_README.md`:
  - [x] Add to capabilities list
  - [x] Add to core components
- [x] Update `docs/GETTING-STARTED.md`:
  - [x] Add Prompt Templates section with examples
- [x] Update `docs/developer-journal.md`:
  - [x] Add Phase 9.1 implementation entry

**Validation:**
```bash
# Documentation should be complete and accurate
```

---

### Acceptance Criteria

- [x] All existing tests pass (378+ baseline)
- [x] 30 new prompt template tests pass (100%)
- [x] All 10 built-in templates render successfully with default parameters
- [x] `from stratifyai.prompts import registry; registry.list()` returns 10 templates
- [x] `registry.render("code_review", code="x=1")` returns `list[Message]`
- [x] `ChatBuilder.with_template("code_review", code=src).chat(...)` works end-to-end
- [x] `stratifyai templates` CLI command lists all templates in Rich table
- [x] `stratifyai chat --template code_review --params "language=python" --file code.py` works
- [x] `GET /api/templates` returns template list with parameters
- [x] `POST /api/templates/code_review/render` returns rendered messages
- [x] User templates in `~/.stratifyai/prompts/` are discovered and listed
- [x] User template overrides built-in with same name
- [x] Invalid parameters raise clear `ValueError` with parameter info
- [x] No new `ruff` or `mypy` errors introduced
- [x] `AGENTS.md`, developer journal, and docs updated
- [x] `str.format_map()` used for substitution (no `eval`, no `exec`)
- [x] YAML loaded with `safe_load()` only

### Files Changed

| Action | File | Lines | Description |
|--------|------|-------|-------------|
| Created | `stratifyai/prompts/__init__.py` | 14 | Package exports + singleton registry |
| Created | `stratifyai/prompts/models.py` | 169 | PromptParameter, PromptTemplate dataclasses |
| Created | `stratifyai/prompts/registry.py` | 228 | PromptRegistry with YAML loading |
| Created | `stratifyai/prompts/templates/code_review.yaml` | 52 | Code review template |
| Created | `stratifyai/prompts/templates/summarize.yaml` | 50 | Summarization template |
| Created | `stratifyai/prompts/templates/chatbot.yaml` | 42 | Chatbot persona template |
| Created | `stratifyai/prompts/templates/explain_concept.yaml` | 52 | Concept explanation template |
| Created | `stratifyai/prompts/templates/analyze_data.yaml` | 51 | Data analysis template |
| Created | `stratifyai/prompts/templates/rag_synthesis.yaml` | 39 | RAG synthesis template |
| Created | `stratifyai/prompts/templates/translate.yaml` | 52 | Translation template |
| Created | `stratifyai/prompts/templates/debug_error.yaml` | 51 | Error debugging template |
| Created | `stratifyai/prompts/templates/commit_message.yaml` | 51 | Git commit message template |
| Created | `stratifyai/prompts/templates/api_docs.yaml` | 54 | API documentation template |
| Created | `tests/test_prompts.py` | 532 | 30 comprehensive tests |
| Created | `docs/PROMPT-TEMPLATES.md` | 371 | Complete user guide |
| Modified | `stratifyai/__init__.py` | +4 | Add PromptTemplate exports |
| Modified | `stratifyai/chat/builder.py` | +75 | Add with_template() method |
| Modified | `cli/stratifyai_cli.py` | +120 | Add templates command, --template flag |
| Modified | `api/main.py` | +80 | Add 3 template endpoints |
| Modified | `AGENTS.md` | +30 | Update structure, phase status |
| Modified | `README.md` | +25 | Add prompt templates section |
| Modified | `ENTERPRISE_README.md` | +8 | Add to capabilities/components |
| Modified | `docs/GETTING-STARTED.md` | +103 | Add Prompt Templates section |
| Modified | `docs/developer-journal.md` | +61 | Add Phase 9.1 entry |

**Total:** 24 files (14 new, 10 modified), ~1,500 lines

### Technical Debt Resolved

- ✅ Prompt patterns duplicated across example scripts
- ✅ No reusable prompt library for common tasks
- ✅ Hardcoded prompts scattered throughout codebase
- ✅ No discoverability mechanism for prompt patterns
- ✅ No parameterization support for system prompts

### Technical Debt Incurred

- ⏳ MCP prompt exposure deferred to Phase 9.2
- ⏳ Frontend template browser not yet implemented
- ⏳ Template versioning/changelog system not included
- ⏳ Template validation UI (pre-render parameter checking) not included

### Next Steps

- **Phase 9.2**: MCP Server Core implementation
- **Phase 9.3**: MCP Server Extended (expose templates as MCP prompts)
- **Future**: Frontend template browser UI tab
- **Future**: Template marketplace/community sharing
