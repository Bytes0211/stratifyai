---
title: "Phase 9.0: Profile System — Built-in Profiles YAML"
labels: ["enhancement", "profiles", "dx", "production"]
milestone: "Phase 9 - Profiles"
assignees: []
---

## Phase 9.0 Step 2 — Built-in Profiles YAML

**Priority:** 💡 HIGH — Required before registry can load profiles
**Estimated effort:** 0.25 days
**Branch:** `dev`
**Status:** ✅ COMPLETE (Mar 1, 2026)

### Context

The profile data model (Step 1) defines the schema and validation logic, but there are no actual profiles to load. This step creates the 6 built-in profiles as a YAML file that ships with the package, following the same pattern as prompt templates (`stratifyai/prompts/templates/*.yaml`).

### References

- **Profile values:** `docs/PROFILE-SYSTEM-PLAN.md` §6
- **YAML schema:** `docs/PROFILE-SYSTEM.md` §4
- **Depends on:** Step 1 (data model) ✅

---

### Task List

#### 9.0.5 — Built-in Profiles YAML
> **File:** `stratifyai/profiles/profiles.yaml`

- [x] Create multi-profile YAML file with `profiles:` root key containing a list of profile entries
- [x] Define 6 built-in profiles matching `PROFILE-SYSTEM-PLAN.md` §6:
  - [x] `fast` — temperature=0.2, max_tokens=1024, reasoning_depth=minimal, speed_vs_accuracy=speed, tags=[speed, realtime]
  - [x] `balanced` — temperature=0.7, max_tokens=2048, reasoning_depth=standard, speed_vs_accuracy=balanced, tool_use=true, tags=[general-purpose]
  - [x] `reasoning` — extends=balanced, temperature=0.2, max_tokens=4000, reasoning_depth=deep, speed_vs_accuracy=accuracy, cost_sensitivity=high, tags=[reasoning, analysis]
  - [x] `vision` — temperature=0.3, max_tokens=2048, multimodal=true, tags=[multimodal, vision]
  - [x] `json` — temperature=0.1, max_tokens=2000, json_mode=true, speed_vs_accuracy=accuracy, tags=[structured, json]
  - [x] `cheap` — temperature=0.4, max_tokens=1024, reasoning_depth=minimal, cost_sensitivity=high, tags=[cost, batch]
- [x] `reasoning` profile uses `extends: balanced` with only 5 override parameters (inherits tool_use, json_mode, multimodal from parent)
- [x] All other profiles specify all 8 parameters explicitly for self-documentation
- [x] Each profile includes descriptive `description` field
- [x] YAML parseable with `yaml.safe_load()`

**Why:** Provides the baseline set of profiles that cover common use cases. The `reasoning` profile demonstrates inheritance via `extends`.

**Validation:**
```python
import yaml
from stratifyai.profiles.models import Profile, merge_parameters

with open("stratifyai/profiles/profiles.yaml") as f:
    data = yaml.safe_load(f)

assert len(data["profiles"]) == 6

# Verify reasoning inherits from balanced
reasoning = next(p for p in data["profiles"] if p["name"] == "reasoning")
balanced = next(p for p in data["profiles"] if p["name"] == "balanced")
assert reasoning["extends"] == "balanced"

effective = merge_parameters(balanced["parameters"], reasoning["parameters"])
assert effective["tool_use"] is True      # inherited
assert effective["reasoning_depth"] == "deep"  # overridden
```

---

### Acceptance Criteria

- [x] `stratifyai/profiles/profiles.yaml` contains 6 profiles
- [x] All profiles parse with `yaml.safe_load()` without errors
- [x] All profile parameters validate against `PARAMETER_DEFINITIONS` via `Profile.validate_parameters()`
- [x] `reasoning` profile's `extends: balanced` field is present and merge produces correct effective parameters
- [x] Inherited parameters (tool_use=true, json_mode=false, multimodal=false) resolve correctly after merge
- [x] Parameter values match `PROFILE-SYSTEM-PLAN.md` §6 table exactly
- [x] No regressions in existing test suite (408 passed)

### Files Changed

| Action | File | Lines | Description |
|--------|------|-------|-------------|
| Created | `stratifyai/profiles/profiles.yaml` | 96 | 6 built-in profiles with inheritance |

**Total:** 1 file (1 new), ~96 lines

### Design Decisions

1. **`reasoning` uses `extends` with only overrides.** Other profiles list all 8 parameters explicitly. This makes inheritance meaningful — reasoning inherits `tool_use=true`, `json_mode=false`, `multimodal=false` from balanced rather than redundantly restating them.
2. **Multi-profile YAML format.** A single file with a `profiles:` list (not one file per profile) matches the schema from `PROFILE-SYSTEM.md` §4 and keeps built-ins co-located.
3. **Descriptive multiline descriptions.** Each profile has a 2-line description explaining its intended use case, aiding discoverability in CLI and API listings.

### Next Steps

- **Step 3:** ProfileRegistry with YAML loading, `extends` resolution, and capability validation
- **Step 4:** Package exports (`stratifyai/profiles/__init__.py`)
