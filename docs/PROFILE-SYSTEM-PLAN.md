# Profile System Implementation Plan — StratifyAI Phase 9

**Document Owner:** Engineering Team  
**Status:** Draft — Implementation Ready  
**Last Updated:** February 28, 2026  

---

## 1. Objectives

- Add reusable profile bundles that standardize StratifyAI behavior across providers and models.
- Provide a consistent configuration layer for temperature, max tokens, reasoning depth, cost sensitivity, multimodal toggle, JSON/schema enforcement, and tool availability.
- Ensure profiles are validated against model capabilities and discoverable via API, CLI, and ChatBuilder.
- Maintain full backwards compatibility for existing API/CLI consumers.

---

## 2. Scope

### In Scope
- Profile data model, registry, and lazy loading.
- Built-in profiles (fast, balanced, reasoning, vision, json, cheap).
- User-defined profiles from `~/.stratifyai/profiles/`.
- Validation against model capability metadata.
- Builder (`ChatBuilder.with_profile()`), CLI (`--profile`), API (`/api/profiles`).
- Testing, documentation, and developer journal entry.

### Out of Scope
- MCP prompt integration (handled in Phase 10.2).
- Enterprise profile governance (Phase 11).
- GUI profile editor (future iteration).
- Persistent profile sync or versioning.

---

## 3. Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Prompt templates (Phase 9.1) | ✅ Complete | Provides YAML-driven configuration pattern. |
| Model catalog capability metadata | ✅ Complete | `catalog/models.json` contains `supports_vision`, `supports_tools`, etc. |
| TrackedLLMClient middleware | ✅ Complete | Required for enforcing profile settings (e.g., budget). |
| CLI + REST architecture | ✅ Complete | Extension points already exist. |

---

## 4. Architecture Overview

```
                   ┌───────────────────────────┐
                   │  stratifyai/profiles/     │
                   │  ├── models.py            │
Builtin YAML  ───▶  │  ├── registry.py         │  ── user overrides from ~/.stratifyai/profiles/
                   │  └── profiles.yaml        │
                   └──────────┬────────────────┘
                              │
           ┌──────────────────┴──────────────────┐
           │                     │                │
    ChatBuilder             CLI/REST         Tests & Docs
(with_profile)       (--profile / API)   (unit & integration)
```

- Profiles are loaded lazily via a singleton registry, similar to prompt templates.
- Built-in profiles ship with the package; user profiles override or extend them.
- Validation ensures each profile parameter is compatible with the target model/provider.
- Effective configuration merges: explicit request params > profile params > defaults.

---

## 5. Data Model

### `ProfileParameter` (enum-like metadata)
- `name: str` (temperature, max_tokens, etc.)
- `type: Literal["number","integer","boolean","string","select"]`
- `description: str`
- `min_value: float | None`
- `max_value: float | None`
- `choices: list[str] | None`
- `default: Any | None`

### `Profile` (dataclass)
- `name: str`
- `description: str`
- `parameters: dict[str, Any]` (e.g., `{"temperature": 0.2}`)
- `tags: list[str]` (e.g., `["speed","cost"]`)
- `extends: str | None` (optional parent profile name for inheritance)
- `source: Literal["builtin","user"]`
- `notes: str | None`

### Effective Configuration Resolution
1. Start with defaults from `ChatBuilder` or API request.
2. Apply profile parameters.
3. Apply explicit overrides from the user.
4. Validate final configuration.

---

## 6. Built-in Profiles (`stratifyai/profiles/profiles.yaml`)

| Profile   | Temperature | Max Tokens | Reasoning Depth | Speed vs Accuracy | Cost Sensitivity | Multimodal | JSON Mode | Tool Use | Tags |
|-----------|-------------|------------|-----------------|-------------------|------------------|------------|-----------|----------|------|
| fast      | 0.2         | 1024       | minimal         | speed             | medium           | false      | false     | false    | speed, realtime |
| balanced  | 0.7         | 2048       | standard        | balanced          | medium           | false      | false     | true     | general-purpose |
| reasoning | 0.2         | 4000       | deep            | accuracy          | high             | false      | false     | true     | reasoning |
| vision    | 0.3         | 2048       | standard        | balanced          | medium           | true       | false     | false    | multimodal |
| json      | 0.1         | 2000       | standard        | accuracy          | medium           | false      | true      | false    | structured,json |
| cheap     | 0.4         | 1024       | minimal         | speed             | high             | false      | false     | false    | cost |

---

## 7. Validation Rules

- `temperature` must be within `0.0 ≤ x ≤ 2.0` and respect any provider-imposed constraints.
- `max_tokens` must be ≤ model `api_max_input` (if provided).
- `reasoning_depth` is advisory; map to provider-specific parameters where applicable.
- `speed_vs_accuracy` and `cost_sensitivity` influence router hints (optional integration).
- `multimodal = true` requires `supports_vision = true`.
- `json_mode = true` requires `supports_json_mode = true` (if metadata exists). Otherwise, restrict to providers/models known to support JSON mode.
- `tool_use = true` requires `supports_tools = true`.

Validation occurs:
1. When loading profiles (structure).
2. When applying profiles to a specific provider/model (capability check).
3. Prior to invocation in ChatBuilder/API.

---

## 8. Registry Implementation (`stratifyai/profiles/registry.py`)

- Singleton, lazy-loaded on first access.
- Load order:
  1. Built-in YAML.
  2. User overrides from `~/.stratifyai/profiles/*.yaml`.
- Supports inheritance chains by resolving the `extends` field during load (detecting cycles and merging parent parameters before applying overrides).
- Methods:
  - `list(tag: str | None = None, source: str | None = None) -> list[Profile]`
  - `get(name: str) -> Profile`
  - `render(name: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]` (returns effective parameters)
  - `validate(name: str, provider: str, model: str) -> None` (raises if incompatible)
  - `register(profile: Profile)` (for programmatic additions)

---

## 9. ChatBuilder Integration

- Add `_profile: Profile | None` attribute.
- New method: `with_profile(name: str, **override_params)`.
  - Fetch profile from registry.
  - Merge overrides into profile parameters.
  - Store validated result in `_profile_config`.
- Modify `_build_messages` to apply profile parameters via `ChatRequest`.
- Ensure explicit method overrides (`with_temperature`) trump profile values.
- When a profile specifies `speed_vs_accuracy` or `cost_sensitivity`, surface those hints to the router by selecting the matching `RoutingStrategy` (speed → latency, balanced → hybrid, accuracy/high cost → quality).

---

## 10. CLI & API Extensions

### CLI (`cli/stratifyai_cli.py`)
- Update `chat` command with `--profile` option and `--profile-param key=value` pairs.
- `templates` command unaffected.
- Add `profiles` command with optional `--tag`, `--source`, `--verbose`.

### API (`api/main.py`)
- `GET /api/profiles`: list metadata (name, description, tags, source).
- `GET /api/profiles/{name}`: detail view (full config, capability hints).
- `POST /api/profiles/{name}/validate`: validate against provider/model.
- `POST /api/profiles/{name}/resolve`: return effective configuration given optional overrides.

---

## 11. Testing Strategy

### Unit Tests
- `tests/test_profiles.py`
  - Registry loading, overrides, duplicate handling.
  - Validation errors (temperature range, capability mismatch).
  - Render behavior with overrides.
- `tests/test_chat_builder.py`
  - `with_profile()` interactions with other builder methods.
  - Precedence of overrides vs profile vs defaults.

### Integration Tests
- CLI: `stratifyai profiles`, `stratifyai chat --profile ...`.
- API: `/api/profiles/*` endpoints with mocked providers.
- Model capability cases (vision-enabled vs text-only).

---

## 12. Documentation Updates

- **New doc:** `docs/PROFILE-SYSTEM.md` (user guide, YAML schema, examples).
- **Existing:** update `PRD-StratifyAI-WORKFLOW-ROADMAP.md`, `DEV-SPEC-StratifyAI-WORKFLOW.md`, `AGENTS.md`, `README.md` (summary section), `developer-journal.md` (upon completion).
- Sample files in `examples/` (e.g., `profile_demo.py`).

---

## 13. Rollout Plan

1. Implement profile data model + registry.
2. Ship built-in profiles YAML.
3. Add CLI/API/ChatBuilder integration.
4. Write unit + integration tests.
5. Update documentation and developer journal.
6. QA pass with regression suite.

---

## 14. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Profile conflicts with explicit overrides | Medium | Medium | Enforce clear precedence; document behavior. |
| Capability mismatch late in pipeline | Medium | High | Validate on `with_profile()` and API resolve step. |
| User YAML schema errors | Medium | Low | Provide schema file + detailed error messages. |
| Profiles drift from capability metadata | Low | Medium | Add regression tests referencing catalog metadata. |

---

## 15. Success Criteria

- Profiles available via CLI, API, and ChatBuilder.
- Built-in profiles validated against top providers/models.
- User-defined profiles load without daemon restart.
- No regressions in existing tests; profile tests added.
- Documentation published with examples and troubleshooting.

---

## 16. Open Questions

1. Profiles support nested inheritance via the `extends` field (implemented in this plan).
2. Profiles influence router strategy by mapping `speed_vs_accuracy` / `cost_sensitivity` to the appropriate `RoutingStrategy`.
3. Profile metadata will remain internal for now (no CLI/API exposure in Phase 9).

---