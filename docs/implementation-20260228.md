# Profile System Implementation (Phase 9)
## Problem
StratifyAI lacks reusable configuration bundles. Users manually configure temperature, max_tokens, reasoning depth, etc. per-request. Profiles provide a named, validated, inheritable configuration layer between model selection and prompt templates.
## Current State
* No profile code exists in `stratifyai/`.
* Design docs finalized: `docs/PROFILE-SYSTEM.md` (user guide), `docs/PROFILE-SYSTEM-PLAN.md` (engineering plan).
* Prompt template system (`stratifyai/prompts/`) provides the architectural pattern to follow: `models.py` (dataclasses) → `registry.py` (singleton, lazy-load, YAML) → `__init__.py` (exports + singleton) → builder/CLI/API integration.
* `PROVIDER_CONSTRAINTS` in `stratifyai/config.py` already defines per-provider temperature ranges.
* `catalog/models.json` already contains `supports_vision`, `supports_tools`, `reasoning_model`, `fixed_temperature` metadata needed for capability validation.
## Proposed Changes
### Step 1: Data model — `stratifyai/profiles/models.py`
New file. Two dataclasses:
**`ProfileParameter`** — metadata for a single parameter *type* (not per-profile). There are exactly 8 of these, defined as a module-level constant `PARAMETER_DEFINITIONS: dict[str, ProfileParameter]`. Fields:
* `name: str`
* `type: Literal["number", "integer", "boolean", "string", "select"]`
* `description: str`
* `min_value: float | None` (for number/integer)
* `max_value: float | None` (for number/integer)
* `choices: list[str] | None` (for select)
* `default: Any | None`
This is a *schema* class, not a per-profile value. It defines what `temperature`, `max_tokens`, `reasoning_depth`, `speed_vs_accuracy`, `cost_sensitivity`, `multimodal`, `json_mode`, and `tool_use` accept.
**`Profile`** — a named configuration bundle. Fields:
* `name: str`
* `description: str`
* `parameters: dict[str, Any]` (e.g., `{"temperature": 0.2, "reasoning_depth": "deep"}`)
* `tags: list[str]`
* `extends: str | None` (parent profile name)
* `source: Literal["builtin", "user"]`
* `notes: str | None`
Methods:
* `validate_parameters()` — structural validation only. Checks each key exists in `PARAMETER_DEFINITIONS`, checks types/ranges/choices. Does NOT check model capabilities (that's the registry's job). Raises `ValueError` on failure.
* `to_dict() -> dict` — serialization for API responses.
Module-level utilities:
* `merge_parameters(parent: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]` — shallow merge (child overrides parent). Used by registry for `extends` resolution.
* `PARAMETER_DEFINITIONS` — the 8 `ProfileParameter` instances as a dict keyed by name.
### Step 2: Built-in profiles — `stratifyai/profiles/profiles.yaml`
New file. Contains the 6 built-in profiles from `PROFILE-SYSTEM-PLAN.md` §6:
* `fast` — temperature=0.2, max_tokens=1024, reasoning_depth=minimal, speed_vs_accuracy=speed
* `balanced` — temperature=0.7, max_tokens=2048, reasoning_depth=standard, speed_vs_accuracy=balanced
* `reasoning` — temperature=0.2, max_tokens=4000, reasoning_depth=deep, extends=balanced
* `vision` — temperature=0.3, max_tokens=2048, multimodal=true
* `json` — temperature=0.1, max_tokens=2000, json_mode=true, speed_vs_accuracy=accuracy
* `cheap` — temperature=0.4, max_tokens=1024, reasoning_depth=minimal, cost_sensitivity=high
YAML structure follows the schema from `PROFILE-SYSTEM.md` §4:
```yaml
profiles:
  - name: fast
    description: "Low latency, minimal reasoning"
    parameters:
      temperature: 0.2
      ...
    tags: [speed, realtime]
```
### Step 3: Registry — `stratifyai/profiles/registry.py`
New file. Mirrors `stratifyai/prompts/registry.py` pattern.
**`ProfileRegistry`** class:
* `__init__()` — empty `_profiles` dict, `_loaded = False`.
* `_ensure_loaded()` — lazy init. Loads builtin YAML, then user overrides from `~/.stratifyai/profiles/*.yaml`.
* `_resolve_extends()` — called after all profiles loaded. Walks each profile's `extends` chain, merges parameters via `merge_parameters()`, detects cycles (set of visited names → `ValueError`).
* `load_directory(path, source)` — load all YAML files from a directory.
* `get(name) -> Profile` — raises `KeyError` with available names.
* `list(tag?, source?) -> list[Profile]` — filtered, sorted by name.
* `render(name, overrides?) -> dict[str, Any]` — returns effective parameter map (profile params merged with overrides).
* `validate_for_model(name, provider, model) -> None` — capability validation. Loads model metadata from `MODEL_CATALOG`, checks:
    * `multimodal=true` requires `supports_vision=true`
    * `tool_use=true` requires `supports_tools=true`
    * `json_mode=true` requires known JSON-capable model (heuristic or metadata)
    * `temperature` clamped to `PROVIDER_CONSTRAINTS[provider]` range
    * `fixed_temperature` on model overrides profile temperature
    * Raises `ValueError` with descriptive message on failure.
* `register(profile)` — programmatic add.
YAML loading function `_load_yaml_profiles(path, source) -> list[Profile]` — mirrors `_load_yaml_template()` from prompts registry. Handles multi-profile YAML format.
### Step 4: Package exports — `stratifyai/profiles/__init__.py`
New file. Mirrors `stratifyai/prompts/__init__.py`:
```python
from stratifyai.profiles.models import Profile, ProfileParameter, PARAMETER_DEFINITIONS
from stratifyai.profiles.registry import ProfileRegistry
registry = ProfileRegistry()
```
### Step 5: ChatBuilder integration — `stratifyai/chat/builder.py`
Modify existing file.
* Add `_profile_params: dict | None = None` field to `ChatBuilder` dataclass.
* Add to `_clone()` method.
* New method `with_profile(name: str, **overrides) -> ChatBuilder`:
    1. Import `stratifyai.profiles.registry` (lazy, same as `with_template`).
    2. Get profile, render with overrides.
    3. Store rendered params in `_profile_params`.
    4. Apply `temperature` and `max_tokens` from profile as defaults (only if not already set by explicit `with_temperature()` / `with_max_tokens()`).
    5. Return cloned builder.
* Modify `chat()` method: when resolving `effective_temp` and `effective_max`, check `_profile_params` between explicit args and builder defaults:
    * `effective_temp = temperature ?? self._temperature ?? profile.temperature ?? self.default_temperature`
    * `effective_max = max_tokens ?? self._max_tokens ?? profile.max_tokens ?? self.default_max_tokens`
Precedence: explicit method args > `with_temperature()`/`with_max_tokens()` > profile > defaults. This matches `PROFILE-SYSTEM.md` §14.
### Step 6: CLI integration — `cli/stratifyai_cli.py`
Modify existing file.
**New `profiles` command** (modeled on `templates` command, line 2287):
* Options: `--tag`, `--verbose`, `--source`.
* Rich table: Name, Description, Tags, Source columns (+Parameters in verbose).
* Usage examples footer.
**Modify `chat` command** (line 51):
* Add `--profile` option: `Optional[str]`.
* Add `--profile-param` option: `Optional[str]` (key=value,key=value format like `--params`).
* In `_chat_impl()`: if `--profile` set, load profile from registry, merge `--profile-param` overrides, apply temperature/max_tokens if not already set by flags, validate against selected provider/model.
### Step 7: API integration — `api/main.py`
Add 4 endpoints after the templates section (line ~1324):
* `GET /api/profiles` — list metadata, optional `tag`/`source` query params.
* `GET /api/profiles/{name}` — full profile detail.
* `POST /api/profiles/{name}/validate` — body: `{provider, model, overrides}`, returns `{valid: bool, errors: [...]}`. Uses `registry.validate_for_model()`.
* `POST /api/profiles/{name}/resolve` — body: same as validate, returns effective parameter map. Uses `registry.render()` + validation.
All endpoints gated by `verify_api_key`.
### Step 8: Package registration — `stratifyai/__init__.py`
Add imports and exports for `Profile`, `ProfileParameter`, `ProfileRegistry`, `profiles.registry`.
### Step 9: Tests — `tests/test_profiles.py`
New file. Target: 25-35 tests.
Model/structural tests:
* `ProfileParameter` validation (types, ranges, choices)
* `Profile.validate_parameters()` pass/fail cases
* `merge_parameters()` child overrides parent
* `Profile.to_dict()` serialization
Registry tests:
* Builtin load (6 profiles)
* User override loading
* `extends` resolution (1 level, 2 levels)
* `extends` cycle detection → `ValueError`
* `get()` unknown name → `KeyError`
* `list()` filtering by tag, source
* `render()` with and without overrides
* `validate_for_model()` — multimodal on non-vision model → error
* `validate_for_model()` — tool_use on non-tools model → error
* `validate_for_model()` — temperature clamping for Anthropic (max 1.0)
* `validate_for_model()` — fixed_temperature model overrides profile
Builder tests (add to `tests/test_chat_builder.py`):
* `with_profile()` applies temperature/max_tokens
* Explicit `with_temperature()` trumps profile
* `with_profile()` + `with_template()` composability
* `with_profile()` clones immutably
### Step 10: Documentation updates
* `AGENTS.md` — add Phase 9 as complete, add `stratifyai/profiles/` to project structure, add `profiles` CLI command, update test count.
* `README.md` — brief mention of profiles in features section.
* `developer-journal.md` — completion entry upon finishing.
