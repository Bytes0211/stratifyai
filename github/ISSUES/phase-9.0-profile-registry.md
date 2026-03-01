---
title: "Phase 9.0: Profile System — ProfileRegistry"
labels: ["enhancement", "profiles", "dx", "production"]
milestone: "Phase 9 - Profiles"
assignees: []
---

## Phase 9.0 Step 3 — ProfileRegistry

**Priority:** 💡 HIGH — Core runtime for the profile system
**Estimated effort:** 0.5 days
**Branch:** `dev`
**Status:** ✅ COMPLETE (Mar 1, 2026)

### Context

Steps 1–2 created the data model (`ProfileParameter`, `Profile`, `PARAMETER_DEFINITIONS`) and the 6 built-in profiles YAML. However, there is no runtime to discover, load, resolve inheritance, or validate profiles against model capabilities. This step implements the `ProfileRegistry` — the central access point for all profile operations — mirroring the `stratifyai/prompts/registry.py` pattern.

### References

- **Pattern:** `stratifyai/prompts/registry.py` (PromptRegistry)
- **Data model:** `stratifyai/profiles/models.py` (Step 1) ✅
- **Built-in profiles:** `stratifyai/profiles/profiles.yaml` (Step 2) ✅
- **Provider constraints:** `stratifyai/config.py` → `PROVIDER_CONSTRAINTS`
- **Model metadata:** `stratifyai/catalog_manager.py` → `get_model_metadata()`
- **Depends on:** Step 1 (data model) ✅, Step 2 (built-in YAML) ✅

---

### Task List

#### 9.0.6 — ProfileRegistry Class
> **File:** `stratifyai/profiles/registry.py`

- [x] Create `ProfileRegistry` class with `_profiles: dict[str, Profile]` and `_loaded: bool` state
- [x] Implement `_ensure_loaded()` — lazy init that loads built-in YAML from `stratifyai/profiles/profiles.yaml`, then user overrides from `~/.stratifyai/profiles/*.yaml`, then calls `_resolve_extends()`
- [x] Implement `_resolve_extends()` — walks each profile's `extends` chain, merges parameters via `merge_parameters()`, detects cycles using a visited set (raises `ValueError`), warns on unknown parent names
- [x] Implement `load_directory(path, source)` — loads all `.yaml`/`.yml` files from a directory, returns count of profiles loaded
- [x] Implement `get(name) -> Profile` — raises `KeyError` with available profile names on miss
- [x] Implement `list(tag?, source?) -> list[Profile]` — filtered and sorted by name
- [x] Implement `render(name, overrides?) -> dict[str, Any]` — returns effective parameter map (profile params merged with overrides), validates each value against `PARAMETER_DEFINITIONS`
- [x] Implement `validate_for_model(name, provider, model) -> None` — capability validation using catalog metadata:
  - [x] `multimodal=true` requires `supports_vision=true` in catalog
  - [x] `tool_use=true` requires `supports_tools=true` in catalog
  - [x] `json_mode=true` on `reasoning_model=true` → error
  - [x] `fixed_temperature` on model logs info when profile temperature differs
  - [x] Temperature checked against `PROVIDER_CONSTRAINTS[provider]` range
  - [x] Collects all errors and raises a single `ValueError`
- [x] Implement `register(profile)` — programmatic add with validation

**Why:** The registry is the single access point for all profile operations. Lazy loading avoids startup cost. Inheritance resolution after all profiles are loaded ensures parent profiles are available regardless of load order.

**Validation:**
```python
from stratifyai.profiles.registry import ProfileRegistry
reg = ProfileRegistry()

# Loads 6 built-in profiles
assert len(reg.list()) == 6

# extends resolution: reasoning inherits from balanced
r = reg.get("reasoning")
assert r.parameters["tool_use"] is True        # inherited from balanced
assert r.parameters["reasoning_depth"] == "deep" # overridden

# render with overrides
params = reg.render("balanced", overrides={"temperature": 0.9})
assert params["temperature"] == 0.9

# validate_for_model catches incompatible profiles
try:
    reg.validate_for_model("vision", "openai", "gpt-4-turbo")
except ValueError:
    pass  # gpt-4-turbo does not support vision
```

---

#### 9.0.7 — YAML Loading Helper
> **File:** `stratifyai/profiles/registry.py`

- [x] Implement `_load_yaml_profiles(path, source) -> list[Profile]` module-level function
- [x] Support multi-profile format (`profiles:` root key with list of entries)
- [x] Support single-profile format (plain mapping with `name` field)
- [x] Call `Profile.validate_parameters()` on each loaded profile
- [x] Skip invalid entries with warning (missing `name` field)
- [x] Raise `ImportError` with install instructions if PyYAML is missing

**Why:** Separating YAML parsing from the registry class keeps the loading logic testable and reusable. Supports both the built-in multi-profile format and user single-profile files.

---

### Acceptance Criteria

- [x] `from stratifyai.profiles.registry import ProfileRegistry` imports cleanly
- [x] `ProfileRegistry()` lazily loads 6 built-in profiles on first access
- [x] User profiles from `~/.stratifyai/profiles/*.yaml` override built-ins with the same name
- [x] `_resolve_extends()` correctly resolves `reasoning` → `balanced` inheritance (tool_use=true inherited)
- [x] `_resolve_extends()` detects cycles and raises `ValueError` with chain description
- [x] `_resolve_extends()` warns and skips when `extends` references an unknown profile
- [x] `get()` on unknown name raises `KeyError` listing available profiles
- [x] `list()` filters by tag and source, returns sorted results
- [x] `render()` merges profile params with overrides (overrides win), validates result
- [x] `validate_for_model()` rejects vision profile on non-vision model (`gpt-4-turbo`)
- [x] `validate_for_model()` rejects tool_use profile on non-tools model (reasoning models)
- [x] `validate_for_model()` rejects json_mode on reasoning models
- [x] `validate_for_model()` checks temperature against `PROVIDER_CONSTRAINTS` range
- [x] `validate_for_model()` logs info when `fixed_temperature` overrides profile temperature
- [x] `register()` validates parameters before adding
- [x] No regressions in existing test suite (408 passed)

### Files Changed

| Action | File | Lines | Description |
|--------|------|-------|-------------|
| Created | `stratifyai/profiles/registry.py` | 406 | ProfileRegistry class, YAML loading helper, capability validation |

**Total:** 1 file (1 new), ~406 lines

### Design Decisions

1. **Mirrors `prompts/registry.py` pattern.** Same lazy-load, same `_ensure_loaded()` guard, same `get/list/register` API shape. Reduces cognitive overhead for contributors familiar with the prompts system.
2. **Lazy imports for `catalog_manager` and `config`.** `validate_for_model()` imports `get_model_metadata` and `PROVIDER_CONSTRAINTS` inside the method body to avoid circular imports and keep the registry importable without loading the full catalog at module level.
3. **Inheritance resolved after all profiles loaded.** `_resolve_extends()` runs once after both built-in and user profiles are loaded, so a user profile can extend a built-in and vice versa regardless of load order.
4. **Cycle detection via visited set per chain.** Each chain walk tracks visited names independently. If a name appears twice in the same walk, the full chain path is included in the error message for debugging.
5. **`validate_for_model()` collects all errors.** Rather than failing on the first incompatibility, all capability and constraint violations are collected and raised as a single `ValueError` with itemized messages.
6. **`fixed_temperature` logs instead of erroring.** When a model has `fixed_temperature`, the profile temperature is effectively ignored at runtime. This is informational (the builder/provider handles the override), so it logs at info level rather than raising.

### Technical Debt Incurred

- ⏳ No `__init__.py` for the profiles package yet (Step 4)
- ⏳ No tests yet for the registry (Step 9)
- ⏳ `json_mode` validation uses heuristic (reasoning_model flag) rather than explicit `supports_json_mode` catalog field
- ⏳ No `search()` method (unlike PromptRegistry) — can be added if needed

### Next Steps

- **Step 4:** Package exports (`stratifyai/profiles/__init__.py`)
- **Step 5:** ChatBuilder `with_profile()` integration
- **Step 6:** CLI integration (`profiles` command, `--profile` flag)
- **Step 9:** Tests for registry (extends resolution, cycle detection, validate_for_model)
