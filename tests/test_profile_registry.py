"""Tests for the ProfileRegistry (Phase 9.0 Step 3).

Covers: lazy loading, built-in profiles, user overrides, extends resolution,
cycle detection, get/list/render/register/validate_for_model, and YAML loading.
"""

from __future__ import annotations

import logging
import textwrap
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from stratifyai.profiles.models import (
    PARAMETER_DEFINITIONS,
    Profile,
    merge_parameters,
)
from stratifyai.profiles.registry import ProfileRegistry, _load_yaml_profiles

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fresh_registry() -> ProfileRegistry:
    """Return a new registry (not yet loaded)."""
    return ProfileRegistry()


def _write_yaml(directory: Path, filename: str, content: str) -> Path:
    """Write a YAML string to *directory/filename* and return the path."""
    p = directory / filename
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


# =========================================================================
# Data-model smoke tests (Profile + ProfileParameter)
# =========================================================================


class TestProfileParameter:
    """Quick sanity checks for ProfileParameter.validate()."""

    def test_validate_number_in_range(self):
        p = PARAMETER_DEFINITIONS["temperature"]
        assert p.validate(0.5) == 0.5

    def test_validate_number_out_of_range(self):
        p = PARAMETER_DEFINITIONS["temperature"]
        with pytest.raises(ValueError, match="must be <="):
            p.validate(3.0)

    def test_validate_integer(self):
        p = PARAMETER_DEFINITIONS["max_tokens"]
        assert p.validate(512) == 512

    def test_validate_integer_too_low(self):
        p = PARAMETER_DEFINITIONS["max_tokens"]
        with pytest.raises(ValueError, match="must be >="):
            p.validate(0)

    def test_validate_boolean_ok(self):
        p = PARAMETER_DEFINITIONS["multimodal"]
        assert p.validate(True) is True

    def test_validate_boolean_wrong_type(self):
        p = PARAMETER_DEFINITIONS["multimodal"]
        with pytest.raises(ValueError, match="must be a boolean"):
            p.validate("yes")

    def test_validate_select_ok(self):
        p = PARAMETER_DEFINITIONS["reasoning_depth"]
        assert p.validate("deep") == "deep"

    def test_validate_select_invalid(self):
        p = PARAMETER_DEFINITIONS["reasoning_depth"]
        with pytest.raises(ValueError, match="must be one of"):
            p.validate("extreme")

    def test_validate_none_returns_default(self):
        p = PARAMETER_DEFINITIONS["temperature"]
        assert p.validate(None) == p.default


class TestProfile:
    """Profile dataclass tests."""

    def test_validate_parameters_valid(self):
        profile = Profile(
            name="test",
            parameters={"temperature": 0.5, "max_tokens": 1024},
        )
        profile.validate_parameters()  # should not raise

    def test_validate_parameters_invalid_value(self):
        profile = Profile(
            name="bad",
            parameters={"temperature": 99.0},
        )
        with pytest.raises(ValueError, match="invalid parameters"):
            profile.validate_parameters()

    def test_validate_parameters_unknown_key_warns(self):
        profile = Profile(
            name="odd",
            parameters={"temperature": 0.5, "banana": True},
        )
        with pytest.warns(match="Unknown profile parameter 'banana'"):
            profile.validate_parameters()

    def test_to_dict(self):
        profile = Profile(
            name="x",
            description="Desc",
            parameters={"temperature": 0.5},
            tags=["a"],
            extends="base",
            source="user",
            notes="note",
        )
        d = profile.to_dict()
        assert d["name"] == "x"
        assert d["extends"] == "base"
        assert d["source"] == "user"
        assert d["notes"] == "note"
        assert d["tags"] == ["a"]


class TestMergeParameters:
    """merge_parameters() utility."""

    def test_child_overrides_parent(self):
        parent = {"temperature": 0.7, "max_tokens": 2048}
        child = {"temperature": 0.2}
        merged = merge_parameters(parent, child)
        assert merged["temperature"] == 0.2
        assert merged["max_tokens"] == 2048

    def test_child_adds_new_keys(self):
        merged = merge_parameters({"a": 1}, {"b": 2})
        assert merged == {"a": 1, "b": 2}


# =========================================================================
# YAML loading helper
# =========================================================================


class TestLoadYamlProfiles:
    """_load_yaml_profiles() tests."""

    def test_load_multi_profile_format(self):
        with TemporaryDirectory() as tmpdir:
            _write_yaml(
                Path(tmpdir),
                "profiles.yaml",
                """\
                profiles:
                  - name: alpha
                    description: Alpha profile
                    parameters:
                      temperature: 0.3
                    tags: [test]
                  - name: beta
                    description: Beta profile
                    parameters:
                      temperature: 0.9
                    tags: [test]
            """,
            )
            profiles = _load_yaml_profiles(
                Path(tmpdir) / "profiles.yaml", source="builtin"
            )
            assert len(profiles) == 2
            names = {p.name for p in profiles}
            assert names == {"alpha", "beta"}
            assert all(p.source == "builtin" for p in profiles)

    def test_load_single_profile_format(self):
        with TemporaryDirectory() as tmpdir:
            _write_yaml(
                Path(tmpdir),
                "solo.yaml",
                """\
                name: solo
                description: Single profile
                parameters:
                  temperature: 0.1
                tags: [single]
            """,
            )
            profiles = _load_yaml_profiles(Path(tmpdir) / "solo.yaml", source="user")
            assert len(profiles) == 1
            assert profiles[0].name == "solo"
            assert profiles[0].source == "user"

    def test_missing_name_skipped_with_warning(self, caplog):
        with TemporaryDirectory() as tmpdir:
            _write_yaml(
                Path(tmpdir),
                "bad.yaml",
                """\
                profiles:
                  - description: no name here
                    parameters:
                      temperature: 0.5
            """,
            )
            with caplog.at_level(logging.WARNING):
                profiles = _load_yaml_profiles(Path(tmpdir) / "bad.yaml", source="user")
            assert len(profiles) == 0
            assert "missing 'name'" in caplog.text

    def test_invalid_yaml_structure_raises(self):
        with TemporaryDirectory() as tmpdir:
            _write_yaml(
                Path(tmpdir),
                "bad.yaml",
                """\
                description: no name and no profiles key
            """,
            )
            with pytest.raises(ValueError, match="missing 'profiles' list"):
                _load_yaml_profiles(Path(tmpdir) / "bad.yaml", source="user")

    def test_non_dict_yaml_raises(self):
        with TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "list.yaml"
            p.write_text("- item1\n- item2\n", encoding="utf-8")
            with pytest.raises(ValueError, match="Expected a YAML mapping"):
                _load_yaml_profiles(p, source="user")

    def test_invalid_parameter_values_raise(self):
        with TemporaryDirectory() as tmpdir:
            _write_yaml(
                Path(tmpdir),
                "bad_params.yaml",
                """\
                name: bad_params
                parameters:
                  temperature: 999.0
            """,
            )
            with pytest.raises(ValueError, match="invalid parameters"):
                _load_yaml_profiles(Path(tmpdir) / "bad_params.yaml", source="user")


# =========================================================================
# ProfileRegistry — loading & lazy init
# =========================================================================


class TestRegistryLoading:
    """Lazy loading, built-in profiles, user directory loading."""

    def test_lazy_load_not_loaded_before_access(self):
        reg = _fresh_registry()
        assert reg._loaded is False

    def test_lazy_load_triggers_on_list(self):
        reg = _fresh_registry()
        _ = reg.list()
        assert reg._loaded is True

    def test_lazy_load_triggers_on_get(self):
        reg = _fresh_registry()
        # Will trigger load then attempt to get "fast"
        profile = reg.get("fast")
        assert profile.name == "fast"

    def test_loads_six_builtin_profiles(self):
        reg = _fresh_registry()
        profiles = reg.list()
        assert len(profiles) == 6
        names = {p.name for p in profiles}
        assert names == {"fast", "balanced", "reasoning", "vision", "json", "cheap"}

    def test_all_builtins_have_source_builtin(self):
        reg = _fresh_registry()
        for p in reg.list():
            assert p.source == "builtin"

    def test_load_directory_returns_count(self):
        reg = _fresh_registry()
        with TemporaryDirectory() as tmpdir:
            _write_yaml(
                Path(tmpdir),
                "custom1.yaml",
                """\
                name: custom1
                parameters:
                  temperature: 0.5
            """,
            )
            _write_yaml(
                Path(tmpdir),
                "custom2.yaml",
                """\
                name: custom2
                parameters:
                  temperature: 0.8
            """,
            )
            count = reg.load_directory(Path(tmpdir), source="user")
            assert count == 2

    def test_load_directory_nonexistent_returns_zero(self):
        reg = _fresh_registry()
        count = reg.load_directory(Path("/nonexistent/dir"), source="user")
        assert count == 0

    def test_load_directory_skips_bad_files(self, caplog):
        reg = _fresh_registry()
        with TemporaryDirectory() as tmpdir:
            # Valid file
            _write_yaml(
                Path(tmpdir),
                "good.yaml",
                """\
                name: good
                parameters:
                  temperature: 0.5
            """,
            )
            # Bad file (not a mapping)
            p = Path(tmpdir) / "bad.yaml"
            p.write_text("- list\n- not\n- mapping\n", encoding="utf-8")

            with caplog.at_level(logging.WARNING):
                count = reg.load_directory(Path(tmpdir), source="user")

            assert count == 1
            assert "Failed to load profiles" in caplog.text

    def test_user_profiles_override_builtins(self):
        """User profile with same name as built-in replaces it."""
        reg = ProfileRegistry()
        # Manually load a user profile that shadows "fast"
        with TemporaryDirectory() as tmpdir:
            _write_yaml(
                Path(tmpdir),
                "fast.yaml",
                """\
                name: fast
                description: User-overridden fast
                parameters:
                  temperature: 0.9
                  max_tokens: 999
                tags: [custom]
            """,
            )
            # Force-load built-ins first
            reg._ensure_loaded()
            _ = reg._profiles["fast"].description

            # Now load user dir — should override
            reg.load_directory(Path(tmpdir), source="user")
            assert reg._profiles["fast"].description.strip() == "User-overridden fast"
            assert reg._profiles["fast"].source == "user"
            assert reg._profiles["fast"].parameters["temperature"] == 0.9


# =========================================================================
# ProfileRegistry — extends / inheritance resolution
# =========================================================================


class TestExtendsResolution:
    """_resolve_extends() tests."""

    def test_reasoning_inherits_from_balanced(self):
        """reasoning extends balanced — should inherit tool_use=True."""
        reg = _fresh_registry()
        r = reg.get("reasoning")
        # reasoning overrides these:
        assert r.parameters["temperature"] == 0.2
        assert r.parameters["max_tokens"] == 4000
        assert r.parameters["reasoning_depth"] == "deep"
        assert r.parameters["speed_vs_accuracy"] == "accuracy"
        # inherited from balanced:
        assert r.parameters["tool_use"] is True
        assert r.parameters["json_mode"] is False
        assert r.parameters["multimodal"] is False

    def test_non_extending_profile_unchanged(self):
        """Profiles without extends keep their declared parameters."""
        reg = _fresh_registry()
        fast = reg.get("fast")
        assert fast.parameters["temperature"] == 0.2
        assert fast.parameters["max_tokens"] == 1024
        assert fast.extends is None

    def test_cycle_detection_raises(self):
        """Circular extends chain should raise ValueError with chain info."""
        reg = ProfileRegistry()
        reg._loaded = True  # skip auto-load
        reg._profiles = {
            "a": Profile(name="a", extends="b", parameters={"temperature": 0.1}),
            "b": Profile(name="b", extends="a", parameters={"temperature": 0.2}),
        }
        with pytest.raises(ValueError, match="Cycle detected"):
            reg._resolve_extends()

    def test_self_referencing_cycle(self):
        reg = ProfileRegistry()
        reg._loaded = True
        reg._profiles = {
            "loop": Profile(
                name="loop", extends="loop", parameters={"temperature": 0.1}
            ),
        }
        with pytest.raises(ValueError, match="Cycle detected"):
            reg._resolve_extends()

    def test_unknown_parent_warns_and_skips(self, caplog):
        """extends referencing unknown profile logs warning, no crash."""
        reg = ProfileRegistry()
        reg._loaded = True
        reg._profiles = {
            "child": Profile(
                name="child",
                extends="nonexistent_parent",
                parameters={"temperature": 0.5, "max_tokens": 512},
            ),
        }
        with caplog.at_level(logging.WARNING):
            reg._resolve_extends()

        assert "extends unknown profile 'nonexistent_parent'" in caplog.text
        # Parameters remain unchanged
        assert reg._profiles["child"].parameters["temperature"] == 0.5

    def test_deep_chain_resolution(self):
        """Three-level chain: grandchild → child → parent."""
        reg = ProfileRegistry()
        reg._loaded = True
        reg._profiles = {
            "parent": Profile(
                name="parent",
                parameters={
                    "temperature": 0.7,
                    "max_tokens": 2048,
                    "tool_use": True,
                },
            ),
            "child": Profile(
                name="child",
                extends="parent",
                parameters={"temperature": 0.3},
            ),
            "grandchild": Profile(
                name="grandchild",
                extends="child",
                parameters={"max_tokens": 512},
            ),
        }
        reg._resolve_extends()

        gc = reg._profiles["grandchild"]
        assert gc.parameters["temperature"] == 0.3  # from child
        assert gc.parameters["max_tokens"] == 512  # own override
        assert gc.parameters["tool_use"] is True  # from parent


# =========================================================================
# ProfileRegistry — get()
# =========================================================================


class TestRegistryGet:
    """get() method tests."""

    def test_get_existing_profile(self):
        reg = _fresh_registry()
        profile = reg.get("balanced")
        assert profile.name == "balanced"
        assert isinstance(profile, Profile)

    def test_get_nonexistent_raises_keyerror(self):
        reg = _fresh_registry()
        with pytest.raises(KeyError, match="Profile 'nonexistent' not found"):
            reg.get("nonexistent")

    def test_get_nonexistent_lists_available(self):
        reg = _fresh_registry()
        with pytest.raises(KeyError, match="Available profiles:"):
            reg.get("nope")


# =========================================================================
# ProfileRegistry — list()
# =========================================================================


class TestRegistryList:
    """list() method tests."""

    def test_list_all_sorted_by_name(self):
        reg = _fresh_registry()
        profiles = reg.list()
        names = [p.name for p in profiles]
        assert names == sorted(names)

    def test_list_filter_by_tag(self):
        reg = _fresh_registry()
        speed_profiles = reg.list(tag="speed")
        assert len(speed_profiles) > 0
        for p in speed_profiles:
            assert "speed" in p.tags

    def test_list_filter_by_source(self):
        reg = _fresh_registry()
        builtins = reg.list(source="builtin")
        assert len(builtins) == 6
        for p in builtins:
            assert p.source == "builtin"

    def test_list_filter_by_source_user_empty(self):
        reg = _fresh_registry()
        user_profiles = reg.list(source="user")
        # No user directory set up, should be empty
        assert len(user_profiles) == 0

    def test_list_combined_filters(self):
        """Tag + source filters can be combined."""
        reg = _fresh_registry()
        results = reg.list(tag="reasoning", source="builtin")
        assert len(results) >= 1
        for p in results:
            assert "reasoning" in p.tags
            assert p.source == "builtin"


# =========================================================================
# ProfileRegistry — render()
# =========================================================================


class TestRegistryRender:
    """render() method tests."""

    def test_render_returns_all_parameters(self):
        reg = _fresh_registry()
        params = reg.render("fast")
        assert "temperature" in params
        assert "max_tokens" in params
        assert "reasoning_depth" in params

    def test_render_values_match_profile(self):
        reg = _fresh_registry()
        params = reg.render("fast")
        assert params["temperature"] == 0.2
        assert params["max_tokens"] == 1024
        assert params["reasoning_depth"] == "minimal"

    def test_render_with_overrides(self):
        reg = _fresh_registry()
        params = reg.render("balanced", overrides={"temperature": 0.9})
        assert params["temperature"] == 0.9
        # Other params unchanged
        assert params["max_tokens"] == 2048

    def test_render_overrides_validated(self):
        """Overrides still go through PARAMETER_DEFINITIONS validation."""
        reg = _fresh_registry()
        with pytest.raises(ValueError, match="must be <="):
            reg.render("fast", overrides={"temperature": 5.0})

    def test_render_nonexistent_profile_raises(self):
        reg = _fresh_registry()
        with pytest.raises(KeyError):
            reg.render("does_not_exist")

    def test_render_reasoning_includes_inherited(self):
        """Rendering 'reasoning' should include parameters inherited from 'balanced'."""
        reg = _fresh_registry()
        params = reg.render("reasoning")
        # Overridden by reasoning
        assert params["temperature"] == 0.2
        assert params["reasoning_depth"] == "deep"
        # Inherited from balanced
        assert params["tool_use"] is True


# =========================================================================
# ProfileRegistry — register()
# =========================================================================


class TestRegistryRegister:
    """register() method tests."""

    def test_register_valid_profile(self):
        reg = _fresh_registry()
        custom = Profile(
            name="custom",
            description="Custom test profile",
            parameters={"temperature": 0.42, "max_tokens": 256},
            tags=["test"],
            source="user",
        )
        reg.register(custom)
        assert reg.get("custom").name == "custom"
        assert reg.get("custom").parameters["temperature"] == 0.42

    def test_register_triggers_lazy_load(self):
        reg = _fresh_registry()
        assert reg._loaded is False
        reg.register(
            Profile(name="trigger", parameters={"temperature": 0.5}, source="user")
        )
        assert reg._loaded is True
        # Built-ins should also be available
        assert reg.get("fast").name == "fast"

    def test_register_invalid_parameters_raises(self):
        reg = _fresh_registry()
        bad = Profile(name="bad", parameters={"temperature": 99.0})
        with pytest.raises(ValueError):
            reg.register(bad)

    def test_register_overwrites_existing(self):
        reg = _fresh_registry()
        v1 = Profile(name="dup", parameters={"temperature": 0.1}, source="user")
        v2 = Profile(
            name="dup",
            description="Version 2",
            parameters={"temperature": 0.9},
            source="user",
        )
        reg.register(v1)
        reg.register(v2)
        assert reg.get("dup").description == "Version 2"
        assert reg.get("dup").parameters["temperature"] == 0.9


# =========================================================================
# ProfileRegistry — validate_for_model()
# =========================================================================


class TestValidateForModel:
    """validate_for_model() capability checks against catalog metadata."""

    # --- vision ---

    def test_vision_on_non_vision_model_raises(self):
        """vision profile requires supports_vision; gpt-4-turbo has supports_vision=false."""
        reg = _fresh_registry()
        with pytest.raises(ValueError, match="does not support vision"):
            reg.validate_for_model("vision", "openai", "gpt-4-turbo")

    def test_vision_on_vision_model_passes(self):
        """gpt-4o supports vision — should not raise."""
        reg = _fresh_registry()
        reg.validate_for_model("vision", "openai", "gpt-4o")  # should pass

    # --- tool_use ---

    def test_tool_use_on_non_tools_model_raises(self):
        """reasoning profile has tool_use=True (inherited); o1 has supports_tools=false."""
        reg = _fresh_registry()
        with pytest.raises(ValueError, match="does not support tools"):
            reg.validate_for_model("reasoning", "openai", "o1")

    def test_tool_use_on_tools_model_passes(self):
        """balanced has tool_use=True; gpt-4o supports tools — should pass."""
        reg = _fresh_registry()
        reg.validate_for_model("balanced", "openai", "gpt-4o")

    # --- json_mode on reasoning model ---

    def test_json_mode_on_reasoning_model_raises(self):
        """json profile has json_mode=True; o1 is reasoning_model=True."""
        reg = _fresh_registry()
        with pytest.raises(ValueError, match="reasoning model"):
            reg.validate_for_model("json", "openai", "o1")

    def test_json_mode_on_non_reasoning_model_passes(self):
        """json profile on gpt-4o (not a reasoning model) should pass."""
        reg = _fresh_registry()
        reg.validate_for_model("json", "openai", "gpt-4o")

    # --- fixed_temperature logs info ---

    def test_fixed_temperature_logs_info(self, caplog):
        """When model has fixed_temperature and profile temp differs, log info."""
        reg = _fresh_registry()
        # fast profile has temperature=0.2; o3-mini has fixed_temperature=1.0
        # fast also has tool_use=False so no tool error
        with caplog.at_level(logging.INFO):
            # fast doesn't require vision/tools/json, so only the temp
            # info log should appear (no error).
            # But o3-mini has supports_vision=false and supports_tools=false —
            # fast has multimodal=false, tool_use=false, json_mode=false, so OK.
            reg.validate_for_model("fast", "openai", "o3-mini")

        assert "fixed_temperature" in caplog.text
        assert "will be overridden" in caplog.text

    # --- temperature out of provider range ---

    def test_temperature_outside_provider_range_raises(self):
        """Anthropic max_temperature is 1.0. A profile with temp=1.5 should fail."""
        reg = _fresh_registry()
        # Register a custom profile with temp=1.5
        hot = Profile(
            name="hot",
            parameters={
                "temperature": 1.5,
                "max_tokens": 1024,
                "multimodal": False,
                "json_mode": False,
                "tool_use": False,
            },
            source="user",
        )
        reg.register(hot)
        with pytest.raises(ValueError, match="outside.*allowed range"):
            reg.validate_for_model("hot", "anthropic", "claude-3-haiku-20240307")

    def test_temperature_within_provider_range_passes(self):
        """balanced temp=0.7 is within anthropic's [0, 1] range."""
        reg = _fresh_registry()
        reg.validate_for_model("balanced", "anthropic", "claude-3-5-sonnet-20241022")

    # --- multiple errors collected ---

    def test_multiple_errors_collected_in_single_raise(self):
        """validate_for_model should collect ALL errors, not just the first."""
        reg = _fresh_registry()
        # Create a profile that violates multiple constraints
        multi_bad = Profile(
            name="multi_bad",
            parameters={
                "temperature": 1.5,  # outside anthropic range
                "multimodal": True,  # haiku has vision but let's use a non-vision model
                "tool_use": True,  # need to pick model without tools
                "json_mode": False,
                "max_tokens": 1024,
            },
            source="user",
        )
        reg.register(multi_bad)
        # deepseek-reasoner: supports_vision=false, supports_tools=false,
        # reasoning_model=true, fixed_temperature=1.0
        # deepseek max_temperature=2.0, so temp=1.5 is fine there
        # Let's use anthropic range instead for temp error
        # Actually pick a non-vision, non-tools model on anthropic...
        # Anthropic models all support vision/tools. Use openai o1 instead
        # which has no vision, no tools, is reasoning, and openai max_temp=2.0
        # so temp=1.5 won't error on openai range. Use deepseek-reasoner on deepseek.
        # deepseek max_temp=2.0, so temp=1.5 is fine.
        # To get temp error too, use anthropic. But anthropic models support vision/tools.
        # Let's just verify at least 2 errors with deepseek-reasoner.
        # deepseek-reasoner: supports_vision=false → multimodal error
        #                    supports_tools=false → tool_use error
        with pytest.raises(ValueError) as exc_info:
            reg.validate_for_model("multi_bad", "deepseek", "deepseek-reasoner")
        error_msg = str(exc_info.value)
        assert "does not support vision" in error_msg
        assert "does not support tools" in error_msg

    # --- unknown model (not in catalog) ---

    def test_unknown_model_no_metadata_no_error(self):
        """If model is not in catalog, capability checks are skipped (no crash)."""
        reg = _fresh_registry()
        # This should not raise because there's no metadata to validate against,
        # and there are no provider constraints violations for the balanced profile
        # on openai (temp 0.7 is within [0, 2]).
        reg.validate_for_model("balanced", "openai", "totally-unknown-model-xyz")

    # --- unknown provider (no constraints) ---

    def test_unknown_provider_no_constraints_no_error(self):
        """If provider has no constraints entry, temperature check is skipped."""
        reg = _fresh_registry()
        reg.validate_for_model("fast", "unknown_provider", "some-model")


# =========================================================================
# User override integration (end-to-end with temp directory)
# =========================================================================


class TestUserProfileIntegration:
    """End-to-end tests with user profile directory."""

    def test_user_directory_profiles_loaded(self):
        with TemporaryDirectory() as tmpdir:
            _write_yaml(
                Path(tmpdir),
                "my_profile.yaml",
                """\
                name: my_custom
                description: My custom profile
                parameters:
                  temperature: 0.42
                  max_tokens: 512
                  reasoning_depth: minimal
                  speed_vs_accuracy: speed
                  cost_sensitivity: low
                  multimodal: false
                  json_mode: false
                  tool_use: false
                tags: [custom]
            """,
            )

            with patch(
                "stratifyai.profiles.registry._USER_DIR",
                Path(tmpdir),
            ):
                reg = ProfileRegistry()
                profiles = reg.list()

            names = {p.name for p in profiles}
            assert "my_custom" in names
            custom = next(p for p in profiles if p.name == "my_custom")
            assert custom.source == "user"
            assert custom.parameters["temperature"] == 0.42

    def test_user_profile_extends_builtin(self):
        """A user profile can extend a built-in profile."""
        with TemporaryDirectory() as tmpdir:
            _write_yaml(
                Path(tmpdir),
                "my_reasoning.yaml",
                """\
                name: my_reasoning
                description: Extended reasoning
                extends: balanced
                parameters:
                  temperature: 0.1
                  reasoning_depth: deep
                tags: [custom, reasoning]
            """,
            )

            with patch(
                "stratifyai.profiles.registry._USER_DIR",
                Path(tmpdir),
            ):
                reg = ProfileRegistry()
                p = reg.get("my_reasoning")

            # Own overrides
            assert p.parameters["temperature"] == 0.1
            assert p.parameters["reasoning_depth"] == "deep"
            # Inherited from balanced
            assert p.parameters["tool_use"] is True
            assert p.parameters["max_tokens"] == 2048

    def test_user_profile_overrides_builtin_name(self):
        """User profile with same name as built-in replaces it entirely."""
        with TemporaryDirectory() as tmpdir:
            _write_yaml(
                Path(tmpdir),
                "fast.yaml",
                """\
                name: fast
                description: My custom fast
                parameters:
                  temperature: 0.9
                  max_tokens: 4096
                  reasoning_depth: standard
                  speed_vs_accuracy: balanced
                  cost_sensitivity: low
                  multimodal: false
                  json_mode: false
                  tool_use: true
                tags: [custom]
            """,
            )

            with patch(
                "stratifyai.profiles.registry._USER_DIR",
                Path(tmpdir),
            ):
                reg = ProfileRegistry()
                fast = reg.get("fast")

            assert fast.source == "user"
            assert fast.parameters["temperature"] == 0.9
            assert fast.parameters["max_tokens"] == 4096
            assert fast.description.strip() == "My custom fast"


# =========================================================================
# Edge cases
# =========================================================================


class TestEdgeCases:
    """Miscellaneous edge cases."""

    def test_double_ensure_loaded_idempotent(self):
        """Calling _ensure_loaded() twice should not duplicate profiles."""
        reg = _fresh_registry()
        reg._ensure_loaded()
        count1 = len(reg._profiles)
        reg._ensure_loaded()
        count2 = len(reg._profiles)
        assert count1 == count2

    def test_render_then_modify_does_not_mutate_profile(self):
        """render() returns a new dict — mutating it should not affect the profile."""
        reg = _fresh_registry()
        params = reg.render("fast")
        params["temperature"] = 999  # mutate the returned dict
        # Original profile should be unchanged
        assert reg.get("fast").parameters["temperature"] == 0.2

    def test_list_returns_new_list_each_call(self):
        """list() should return a fresh list, not the internal collection."""
        reg = _fresh_registry()
        list1 = reg.list()
        list2 = reg.list()
        assert list1 is not list2
        assert len(list1) == len(list2)

    def test_profile_tags_present_on_builtins(self):
        """All built-in profiles should have at least one tag."""
        reg = _fresh_registry()
        for p in reg.list():
            assert len(p.tags) >= 1, f"Profile '{p.name}' has no tags"

    def test_all_builtin_profiles_have_all_8_parameters(self):
        """Each built-in profile (after extends resolution) should have all 8 params."""
        reg = _fresh_registry()
        expected_keys = set(PARAMETER_DEFINITIONS.keys())
        for p in reg.list():
            actual_keys = set(p.parameters.keys())
            assert actual_keys == expected_keys, (
                f"Profile '{p.name}' missing params: {expected_keys - actual_keys}"
            )

    def test_render_override_with_none_uses_default(self):
        """Passing None for a parameter in overrides should use the param default."""
        reg = _fresh_registry()
        params = reg.render("fast", overrides={"temperature": None})
        # None → param default (0.7 per PARAMETER_DEFINITIONS)
        assert params["temperature"] == PARAMETER_DEFINITIONS["temperature"].default

    def test_validate_for_model_vision_profile_on_anthropic_vision_model(self):
        """Anthropic Claude 3.5 Sonnet supports vision — vision profile should pass."""
        reg = _fresh_registry()
        reg.validate_for_model("vision", "anthropic", "claude-3-5-sonnet-20241022")

    def test_validate_for_model_cheap_profile_passes_everywhere(self):
        """cheap profile has no special capability requirements — should pass broadly."""
        reg = _fresh_registry()
        # gpt-4o supports everything, cheap asks for nothing special
        reg.validate_for_model("cheap", "openai", "gpt-4o")

    def test_three_level_cycle_detected(self):
        """A → B → C → A should be detected as a cycle."""
        reg = ProfileRegistry()
        reg._loaded = True
        reg._profiles = {
            "a": Profile(name="a", extends="b", parameters={"temperature": 0.1}),
            "b": Profile(name="b", extends="c", parameters={"temperature": 0.2}),
            "c": Profile(name="c", extends="a", parameters={"temperature": 0.3}),
        }
        with pytest.raises(ValueError, match="Cycle detected"):
            reg._resolve_extends()
