"""Profile system for StratifyAI."""

from stratifyai.profiles.models import (
    PARAMETER_DEFINITIONS,
    Profile,
    ProfileParameter,
    merge_parameters,
)
from stratifyai.profiles.registry import ProfileRegistry

# Singleton registry instance
registry = ProfileRegistry()

__all__ = [
    "PARAMETER_DEFINITIONS",
    "Profile",
    "ProfileParameter",
    "ProfileRegistry",
    "merge_parameters",
    "registry",
]
