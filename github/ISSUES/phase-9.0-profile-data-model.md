---
title: "Phase 9.0: Profile System — Data Model"
labels: ["enhancement", "profiles", "dx", "production"]
milestone: "Phase 9 - Profiles"
assignees: []
---

## Phase 9.0 — Profile Data Model

**Priority:** 💡 HIGH — Foundation for the entire profile system
**Estimated effort:** 0.5 days
**Branch:** `dev`
**Status:** ✅ COMPLETE (Mar 1, 2026)

### Context

StratifyAI has no reusable configuration bundles. Users manually configure temperature, max_tokens, reasoning depth, and other behavioral parameters per-request via ChatBuilder, CLI flags, or the API. This creates inconsistency across calls and prevents teams from standardizing model behavior.

This step implements the foundational data model for profiles — the `ProfileParameter` schema class, the `Profile` dataclass, structural validation, and the merge utility for inheritance resolution.

### References

- **User Guide:** `docs/PROFILE-SYSTEM.md`
- **Engineering Plan:** `docs/PROFILE-SYSTEM-PLAN.md`
- **DEV-SPEC:** `docs/DEV-SPEC-StratifyAI-WORKFLOW.md` — Section 6
- **PRD:** `docs/PRD-StratifyAI-WORKFLOW-ROADMAP.md` — Step 3

---

### Task List

#### 9.0.1 — ProfileParameter Schema Class
> **File:** `stratifyai/profiles/models.py`

- [x] Create `ProfileParameter` dataclass with validation for 5 types: number, integer, boolean, string, select
- [x] Support `min_value` / `max_value` range constraints for number and integer types
- [x] Support `choices` list for select type
- [x] Support `default` fallback when value is `None`
- [x] Type coercion: `float()` for number, `int()` for integer
- [x] Raise clear `ValueError` messages with parameter name and constraint details

**Why:** Profiles need a fixed schema that defines what parameters exist and what values they accept. This is the global schema, not per-profile — there are exactly 8 parameter definitions shared across all profiles.

**Validation:**
```python
from stratifyai.profiles.models import PARAMETER_DEFINITIONS
temp = PARAMETER_DEFINITIONS["temperature"]
assert temp.validate(0.5) == 0.5
assert temp.validate(None) == 0.7  # default
# temp.validate(3.0) -> ValueError
```

---

#### 9.0.2 — Parameter Definitions
> **File:** `stratifyai/profiles/models.py`

- [x] Define `PARAMETER_DEFINITIONS: dict[str, ProfileParameter]` with 8 entries:
  - [x] `temperature` — number, range 0.0–2.0, default 0.7
  - [x] `max_tokens` — integer, range 1–1,000,000, default 2048
  - [x] `reasoning_depth` — select, choices: minimal/standard/deep, default standard
  - [x] `speed_vs_accuracy` — select, choices: speed/balanced/accuracy, default balanced
  - [x] `cost_sensitivity` — select, choices: low/medium/high, default medium
  - [x] `multimodal` — boolean, default false
  - [x] `json_mode` — boolean, default false
  - [x] `tool_use` — boolean, default false

**Why:** Fixed schema makes validation deterministic and extensible. Parameter definitions match `PROFILE-SYSTEM-PLAN.md` §5.

**Validation:**
```python
assert len(PARAMETER_DEFINITIONS) == 8
assert PARAMETER_DEFINITIONS["reasoning_depth"].choices == ["minimal", "standard", "deep"]
```

---

#### 9.0.3 — Profile Dataclass
> **File:** `stratifyai/profiles/models.py`

- [x] Create `Profile` dataclass with fields: name, description, parameters, tags, extends, source, notes
- [x] `parameters` is `dict[str, Any]` — values validated against `PARAMETER_DEFINITIONS`
- [x] `extends` is `Optional[str]` for inheritance (resolution deferred to registry)
- [x] `source` is `Literal["builtin", "user"]` for provenance tracking
- [x] Implement `validate_parameters()` — structural validation only:
  - [x] Check each key exists in `PARAMETER_DEFINITIONS`
  - [x] Validate each value via the corresponding `ProfileParameter.validate()`
  - [x] Warn (not raise) on unknown parameter keys
  - [x] Collect all errors and raise a single `ValueError` with all failures
- [x] Implement `to_dict()` for API serialization
- [x] No imports from `stratifyai.config` or `stratifyai.catalog_manager` — data model stays decoupled from catalog

**Why:** Clean separation: structural validation in the model, capability validation in the registry. Mirrors the `PromptTemplate` pattern where the dataclass is catalog-unaware.

**Validation:**
```python
p = Profile(name="test", parameters={"temperature": 0.3, "reasoning_depth": "deep"})
p.validate_parameters()  # passes
bad = Profile(name="bad", parameters={"temperature": 5.0})
bad.validate_parameters()  # raises ValueError
```

---

#### 9.0.4 — Merge Utility
> **File:** `stratifyai/profiles/models.py`

- [x] Implement `merge_parameters(parent, child) -> dict` — shallow merge, child overrides parent
- [x] Returns a new dict (no mutation)

**Why:** Used by the registry (Step 3) to resolve `extends` inheritance chains. Placed in models.py because it operates on raw parameter dicts without needing catalog access.

**Validation:**
```python
merged = merge_parameters({"a": 1, "b": 2}, {"b": 3, "c": 4})
assert merged == {"a": 1, "b": 3, "c": 4}
```

---

### Acceptance Criteria

- [x] All 408 existing tests pass (zero regressions)
- [x] `from stratifyai.profiles.models import Profile, ProfileParameter, PARAMETER_DEFINITIONS, merge_parameters` imports cleanly
- [x] `PARAMETER_DEFINITIONS` contains exactly 8 entries
- [x] `ProfileParameter.validate()` correctly enforces ranges, types, choices, and defaults
- [x] `Profile.validate_parameters()` catches invalid values with descriptive errors
- [x] `Profile.validate_parameters()` warns on unknown keys without raising
- [x] `Profile.to_dict()` returns JSON-serializable dict
- [x] `merge_parameters()` produces correct shallow merge with child precedence
- [x] `Profile.extends` field accepts `str | None` for inheritance
- [x] No imports from `stratifyai.config`, `stratifyai.catalog_manager`, or any provider module
- [x] Module passes `python -c "from stratifyai.profiles.models import ..."` without errors

### Files Changed

| Action | File | Lines | Description |
|--------|------|-------|-------------|
| Created | `stratifyai/profiles/models.py` | 270 | ProfileParameter, Profile, PARAMETER_DEFINITIONS, merge_parameters |

**Total:** 1 file (1 new), ~270 lines

### Design Decisions

1. **`ProfileParameter` is a schema class, not per-profile.** Unlike `PromptParameter` (which varies per template), `ProfileParameter` defines the global set of 8 valid parameter types. All profiles share this schema.
2. **Structural validation only in models.** Capability validation (e.g., `multimodal=true` requires `supports_vision`) needs catalog metadata and belongs in the registry (Step 3). This keeps the data model decoupled.
3. **`extends` is a field, not a resolution mechanism.** The `extends: str | None` field stores the parent name. Actual inheritance resolution (recursive lookup, cycle detection, parameter merging) is handled by the registry after all profiles are loaded.
4. **Warns on unknown keys, doesn't reject.** Future-proofs against custom parameters while still surfacing likely typos.

### Technical Debt Incurred

- ⏳ No `__init__.py` for the profiles package yet (Step 4)
- ⏳ No tests yet for the data model (Step 9)
- ⏳ Capability validation deferred to registry (Step 3)
- ⏳ YAML loading deferred to registry (Step 3)

### Next Steps

- **Step 2:** Built-in profiles YAML (`stratifyai/profiles/profiles.yaml`)
- **Step 3:** ProfileRegistry with YAML loading, inheritance resolution, and capability validation
- **Step 4:** Package exports (`stratifyai/profiles/__init__.py`)
- **Step 5:** ChatBuilder `with_profile()` integration
