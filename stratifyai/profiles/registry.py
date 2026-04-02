"""Profile registry for discovery, loading, and validation.

Mirrors the :mod:`stratifyai.prompts.registry` pattern: lazy-load built-in
YAML profiles on first access, then user overrides from
``~/.stratifyai/profiles/*.yaml``.
"""

from __future__ import annotations

import builtins
import logging
from pathlib import Path
from typing import Any

from stratifyai.profiles.models import (
    PARAMETER_DEFINITIONS,
    Profile,
    merge_parameters,
)

logger = logging.getLogger(__name__)

# Directories
_BUILTIN_PATH = Path(__file__).parent / "profiles.yaml"
_USER_DIR = Path.home() / ".stratifyai" / "profiles"


class ProfileRegistry:
    """Singleton registry for discovering, loading, and rendering profiles.

    Profiles are loaded lazily on first access.  Built-in profiles come from
    ``stratifyai/profiles/profiles.yaml``.  User profiles from
    ``~/.stratifyai/profiles/`` override built-ins with the same name.

    Usage::

        from stratifyai.profiles import registry

        # List all profiles
        for p in registry.list():
            print(p.name, p.description)

        # Get effective parameters
        params = registry.render("fast")
    """

    def __init__(self) -> None:
        self._profiles: dict[str, Profile] = {}
        self._loaded: bool = False

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """Load profiles on first access (lazy)."""
        if self._loaded:
            return
        self._loaded = True

        # Built-in profiles (single YAML file)
        if _BUILTIN_PATH.is_file():
            for profile in _load_yaml_profiles(_BUILTIN_PATH, source="builtin"):
                self._profiles[profile.name] = profile

        # User overrides
        if _USER_DIR.is_dir():
            self.load_directory(_USER_DIR, source="user")

        # Resolve inheritance after all profiles are loaded
        self._resolve_extends()

    def _resolve_extends(self) -> None:
        """Walk ``extends`` chains and merge inherited parameters.

        Detects cycles by tracking visited profile names during each chain
        walk.

        Raises:
            ValueError: If a cycle is detected in the ``extends`` chain.
        """
        resolved: dict[str, dict[str, Any]] = {}

        for name, _profile in self._profiles.items():
            if name in resolved:
                continue

            # Walk the chain collecting ancestors (child → parent order)
            chain: list[str] = []
            visited: set[str] = set()
            current = name

            while current is not None:
                if current in visited:
                    raise ValueError(
                        f"Cycle detected in profile extends chain: "
                        f"{' -> '.join(chain)} -> {current}"
                    )
                visited.add(current)
                chain.append(current)

                parent_name = self._profiles[current].extends
                if parent_name is not None and parent_name not in self._profiles:
                    logger.warning(
                        "Profile '%s' extends unknown profile '%s'; "
                        "ignoring inheritance.",
                        current,
                        parent_name,
                    )
                    break
                current = parent_name

            # Merge from root ancestor down to the leaf
            merged: dict[str, Any] = {}
            for ancestor_name in reversed(chain):
                merged = merge_parameters(
                    merged, self._profiles[ancestor_name].parameters
                )
                resolved[ancestor_name] = dict(merged)

            # Write the fully resolved parameters back
            self._profiles[name].parameters = resolved[name]

    # ------------------------------------------------------------------
    # Directory loading
    # ------------------------------------------------------------------

    def load_directory(self, path: Path, source: str = "user") -> int:
        """Load all YAML profile files from a directory.

        Args:
            path: Directory containing ``.yaml`` / ``.yml`` files.
            source: Label for the source (``"builtin"`` or ``"user"``).

        Returns:
            Number of profiles successfully loaded.
        """
        count = 0
        if not path.is_dir():
            return count

        for yaml_path in sorted(path.glob("*.y*ml")):
            try:
                for profile in _load_yaml_profiles(yaml_path, source=source):
                    self._profiles[profile.name] = profile
                    count += 1
            except Exception as exc:
                logger.warning(
                    "Failed to load profiles from %s: %s", yaml_path.name, exc
                )
        return count

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, profile: Profile) -> None:
        """Register a profile programmatically.

        The profile's parameters are validated on registration.
        """
        self._ensure_loaded()
        profile.validate_parameters()
        self._profiles[profile.name] = profile

    def get(self, name: str) -> Profile:
        """Get a profile by name.

        Args:
            name: The profile name.

        Returns:
            The :class:`Profile` instance.

        Raises:
            KeyError: If the profile is not found (message lists available
                profile names).
        """
        self._ensure_loaded()
        if name not in self._profiles:
            available = sorted(self._profiles.keys())
            raise KeyError(
                f"Profile '{name}' not found. "
                f"Available profiles: {available}"
            )
        return self._profiles[name]

    def list(
        self,
        tag: str | None = None,
        source: str | None = None,
    ) -> builtins.list[Profile]:
        """List profiles with optional filtering.

        Args:
            tag: Filter by tag (e.g., ``"speed"``).
            source: Filter by source (``"builtin"`` or ``"user"``).

        Returns:
            List of matching profiles, sorted by name.
        """
        self._ensure_loaded()
        profiles = list(self._profiles.values())

        if tag:
            profiles = [p for p in profiles if tag in p.tags]
        if source:
            profiles = [p for p in profiles if p.source == source]

        return sorted(profiles, key=lambda p: p.name)

    def render(
        self,
        name: str,
        overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the effective parameter map for a profile.

        Profile parameters are merged with *overrides* (overrides win).
        Each final value is validated against :data:`PARAMETER_DEFINITIONS`.

        Args:
            name: Profile name.
            overrides: Optional parameter overrides.

        Returns:
            A dict of validated, effective parameter values.
        """
        profile = self.get(name)
        effective = dict(profile.parameters)
        if overrides:
            effective = merge_parameters(effective, overrides)

        # Validate merged result
        for key, value in list(effective.items()):
            param_def = PARAMETER_DEFINITIONS.get(key)
            if param_def is not None:
                effective[key] = param_def.validate(value)

        return effective

    def validate_for_model(
        self,
        name: str,
        provider: str,
        model: str,
    ) -> None:
        """Validate a profile against a specific provider/model's capabilities.

        Checks catalog metadata (``supports_vision``, ``supports_tools``,
        ``fixed_temperature``) and provider constraints (temperature range).

        Args:
            name: Profile name.
            provider: Provider key (e.g., ``"anthropic"``).
            model: Model ID (e.g., ``"claude-3-haiku-20240307"``).

        Raises:
            ValueError: If the profile requires capabilities the model
                does not support.
        """
        from stratifyai.catalog_manager import get_model_metadata
        from stratifyai.config import PROVIDER_CONSTRAINTS

        profile = self.get(name)
        params = profile.parameters
        errors: list[str] = []

        metadata = get_model_metadata(provider, model)

        # --- Capability checks against catalog metadata ---
        if metadata:
            # Multimodal requires vision support
            if params.get("multimodal") and not metadata.get("supports_vision"):
                errors.append(
                    f"Profile '{name}' requires multimodal (vision) but "
                    f"model '{model}' does not support vision."
                )

            # Tool use requires tools support
            if params.get("tool_use") and not metadata.get("supports_tools"):
                errors.append(
                    f"Profile '{name}' requires tool_use but "
                    f"model '{model}' does not support tools."
                )

            # JSON mode — heuristic: most modern models support it, but
            # reasoning models and very old models may not.
            if params.get("json_mode") and metadata.get("reasoning_model"):
                errors.append(
                    f"Profile '{name}' requires json_mode but "
                    f"model '{model}' is a reasoning model that may not "
                    f"support structured JSON output."
                )

            # Fixed temperature override
            if "fixed_temperature" in metadata and "temperature" in params:
                fixed = metadata["fixed_temperature"]
                profile_temp = params["temperature"]
                if profile_temp != fixed:
                    logger.info(
                        "Model '%s' has fixed_temperature=%s; profile '%s' "
                        "temperature=%s will be overridden.",
                        model,
                        fixed,
                        name,
                        profile_temp,
                    )

        # --- Provider temperature constraints ---
        constraints = PROVIDER_CONSTRAINTS.get(provider)
        if constraints and "temperature" in params:
            temp = params["temperature"]
            min_t = constraints.get("min_temperature", 0.0)
            max_t = constraints.get("max_temperature", 2.0)
            if temp < min_t or temp > max_t:
                errors.append(
                    f"Profile '{name}' temperature={temp} is outside "
                    f"{provider}'s allowed range [{min_t}, {max_t}]."
                )

        if errors:
            raise ValueError(
                f"Profile '{name}' is incompatible with "
                f"{provider}/{model}:\n" + "\n".join(f"  - {e}" for e in errors)
            )


# -----------------------------------------------------------------------
# YAML loading helper
# -----------------------------------------------------------------------


def _load_yaml_profiles(
    path: Path,
    source: str = "user",
) -> list[Profile]:
    """Load profiles from a single YAML file.

    Supports the multi-profile format used by ``profiles.yaml``::

        profiles:
          - name: fast
            ...
          - name: balanced
            ...

    As well as single-profile files (a plain mapping with ``name``).

    Args:
        path: Path to the ``.yaml`` file.
        source: Source label (``"builtin"`` or ``"user"``).

    Returns:
        A list of :class:`Profile` instances.

    Raises:
        ImportError: If PyYAML is not installed.
        ValueError: If the YAML structure is invalid.
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required to load YAML profiles. "
            "Install it with: pip install pyyaml"
        )

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path.name}")

    # Multi-profile format: { profiles: [...] }
    raw_profiles = data.get("profiles")
    if raw_profiles is None:
        # Single-profile format: { name: ..., parameters: ... }
        if "name" not in data:
            raise ValueError(
                f"Profile YAML {path.name} missing 'profiles' list "
                f"or 'name' field."
            )
        raw_profiles = [data]

    profiles: list[Profile] = []
    for entry in raw_profiles:
        if not isinstance(entry, dict) or "name" not in entry:
            logger.warning(
                "Skipping invalid profile entry in %s: missing 'name'",
                path.name,
            )
            continue

        profile = Profile(
            name=entry["name"],
            description=entry.get("description", "").strip(),
            parameters=entry.get("parameters", {}),
            tags=entry.get("tags", []),
            extends=entry.get("extends"),
            source=source,
            notes=entry.get("notes"),
        )
        profile.validate_parameters()
        profiles.append(profile)

    return profiles
