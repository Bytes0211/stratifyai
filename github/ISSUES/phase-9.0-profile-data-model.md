# Phase 9.0 — Profile Data Model & Registry

**Status:** Planned  
**Owner:** @stratifyai-core  
**Target Release:** Phase 9 (Profiles)  
**Last Updated:** 2026-02-28

---

## 1. Summary

Implement the foundational profile data model and registry for StratifyAI. Profiles encapsulate reusable configuration bundles (temperature, max tokens, reasoning depth, cost sensitivity, multimodal flag, JSON enforcement, tool availability, router hints) that can be applied across providers and models. This issue covers the core infrastructure: dataclasses, validation logic, YAML loading with inheritance, and tests. Follow-up issues will handle CLI/API/ChatBuilder integration.

---

## 2. Goals

- Define strongly-typed profile dataclasses (`Profile`, `ProfileParameter`).
- Implement a lazy-loaded profile registry that supports inheritance (`extends`), user overrides, and validation against model capabilities.
- Provide built-in profiles (fast, balanced, reasoning, vision, json, cheap) with YAML definitions.
- Ensure extensibility for future profile additions (router hints, structured outputs).

---

## 3. Acceptance Criteria

- [ ] `stratifyai/profiles/models.py` contains dataclasses with full type hints and docstrings.
- [ ] `stratifyai/profiles/registry.py` loads built-in profiles and user overrides, resolves inheritance, and validates configurations.
- [ ] Built-in profiles defined in `stratifyai/profiles/profiles.yaml` pass validation.
- [ ] Validation detects capability mismatches (vision, JSON mode, tool use, etc.) when rendered for a provider/model.
- [ ] Unit tests cover registry loading, inheritance, validation, and override precedence.
- [ ] Developer documentation (docstrings + inline comments) explains how to add future profiles.

---

## 4. Deliverables

1. **Data Model**
   - `ProfileParameter` metadata (name, type, description, ranges, choices, defaults).
   - `Profile` dataclass (name, description, parameters dict, tags, extends, source, notes).

2. **Registry**
   - Singleton registry with lazy loading.
   - Load order: built-in YAML → user overrides (`~/.stratifyai/profiles/`).
   - Methods: `list`, `get`, `render`, `validate`, `register`, `reload` (optional).
   - Inheritance resolution with cycle detection.
   - Validation against model catalog capabilities.

3. **Built-in Profiles**
   - `stratifyai/profiles/profiles.yaml` with six baseline profiles.
   - Documentation of intended usage and compatibility notes.

4. **Tests**
   - New test module `tests/test_profiles.py`.
   - Coverage for happy paths, inheritance, validation failures, user overrides.

---

## 5. Implementation Plan

1. **Scaffold Module & Dataclasses**
   - Create `stratifyai/profiles/models.py` with dataclasses and validation helpers.
   - Add convenience enums/constants for parameter types/choices.

2. **Registry & Loader**
   - Implement registry class with internal cache.
   - YAML parsing via `yaml.safe_load` (handle missing keys, wrong types).
   - Merge profiles with inheritance; raise descriptive errors on cycles or missing parents.

3. **Built-in Profiles**
   - Translate roadmap defaults into YAML.
   - Add tags for filtering (speed, reasoning, etc.).

4. **Validation Logic**
   - Integrate model catalog metadata (vision/tools/json flags).
   - Create helper that accepts provider/model and raises informative errors.

5. **Testing**
   - Use fixtures/mocks for catalog and capability checks.
  - Test user override directory via temporary path.

6. **Documentation & Cleanup**
   - Docstrings, inline comments, and developer journal update.
   - Prepare follow-up issues for CLI/API/ChatBuilder integration.

---

## 6. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Inheritance loops cause infinite recursion | Low | High | Add cycle detection with ancestor tracking. |
| Capability metadata missing for new models | Medium | Medium | Fallback warnings + regression tests referencing catalog schema. |
| User YAML errors reduce discoverability | Medium | Low | Provide clear error messages and future docs (`docs/PROFILE-SYSTEM.md`). |
| Conflicting overrides lead to unexpected behavior | Medium | Medium | Document precedence (explicit > profile > defaults) and enforce in tests. |

---

## 7. Related Work

- `docs/DEV-SPEC-StratifyAI-WORKFLOW.md` — Phase 9 implementation details.
- `docs/PROFILE-SYSTEM-PLAN.md` — Engineering plan for profiles (this issue covers sections 5–8).
- `docs/PROFILE-SYSTEM.md` — User guide (to be completed as parts land).

---

## 8. Follow-up Issues

1. **Phase 9.1** — Profile integration with ChatBuilder/CLI/API.
2. **Phase 9.2** — Update documentation and developer journal.
3. **Phase 9.3** — Profile-aware routing enhancements (optional).
4. **Phase 9.4** — Profile support surfaced in MCP server.

---

## 9. Checklist

- [ ] Dataclasses merged with type hints and docstrings.
- [ ] Registry loads built-ins and user overrides.
- [ ] Inheritance and validation scripts implemented.
- [ ] Built-in profiles validated against catalog.
- [ ] Tests added and passing locally.
- [ ] Documentation updated; follow-up issues opened.

---