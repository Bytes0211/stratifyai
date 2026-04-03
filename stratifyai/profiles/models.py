"""Profile data models for StratifyAI.

Profiles are reusable configuration bundles that standardize model behavior
across providers. This module defines the data model and structural validation.

Capability validation (e.g., checking ``supports_vision`` against catalog
metadata) is handled by the registry, not here — keeping the data model
decoupled from the catalog.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class ProfileParameter:
    """Schema definition for a single profile parameter type.

    There are exactly 8 of these, defined in :data:`PARAMETER_DEFINITIONS`.
    Each describes what values a given parameter key accepts across all
    profiles.

    Attributes:
        name: Parameter key (e.g., ``"temperature"``).
        type: Value type for validation.
        description: Human-readable description.
        min_value: Minimum for number/integer types.
        max_value: Maximum for number/integer types.
        choices: Valid values for select type.
        default: Default value when not specified in a profile.
    """

    name: str
    type: Literal["number", "integer", "boolean", "string", "select"] = "string"
    description: str = ""
    min_value: float | None = None
    max_value: float | None = None
    choices: list[str] | None = None
    default: Any = None

    def validate(self, value: Any) -> Any:
        """Validate and coerce a parameter value against this schema.

        Args:
            value: The value to validate.

        Returns:
            The validated (and possibly coerced) value.

        Raises:
            ValueError: If the value fails validation.
        """
        if value is None:
            return self.default

        if self.type == "number":
            try:
                value = float(value)
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"Parameter '{self.name}' must be a number, got: {value!r}"
                ) from e
            if self.min_value is not None and value < self.min_value:
                raise ValueError(
                    f"Parameter '{self.name}' must be >= {self.min_value}, got: {value}"
                )
            if self.max_value is not None and value > self.max_value:
                raise ValueError(
                    f"Parameter '{self.name}' must be <= {self.max_value}, got: {value}"
                )

        elif self.type == "integer":
            try:
                value = int(value)
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"Parameter '{self.name}' must be an integer, got: {value!r}"
                ) from e
            if self.min_value is not None and value < self.min_value:
                raise ValueError(
                    f"Parameter '{self.name}' must be >= {int(self.min_value)}, "
                    f"got: {value}"
                )
            if self.max_value is not None and value > self.max_value:
                raise ValueError(
                    f"Parameter '{self.name}' must be <= {int(self.max_value)}, "
                    f"got: {value}"
                )

        elif self.type == "boolean":
            if not isinstance(value, bool):
                raise ValueError(
                    f"Parameter '{self.name}' must be a boolean, got: {value!r}"
                )

        elif self.type == "select":
            if self.choices and str(value) not in self.choices:
                raise ValueError(
                    f"Parameter '{self.name}' must be one of "
                    f"{self.choices}, got: {value!r}"
                )

        return value


# ---------------------------------------------------------------------------
# Global parameter definitions — the fixed schema for all profiles
# ---------------------------------------------------------------------------

PARAMETER_DEFINITIONS: dict[str, ProfileParameter] = {
    "temperature": ProfileParameter(
        name="temperature",
        type="number",
        description="Sampling temperature (0.0 = deterministic, 2.0 = creative)",
        min_value=0.0,
        max_value=2.0,
        default=0.7,
    ),
    "max_tokens": ProfileParameter(
        name="max_tokens",
        type="integer",
        description="Maximum tokens to generate in the response",
        min_value=1,
        max_value=1_000_000,
        default=2048,
    ),
    "reasoning_depth": ProfileParameter(
        name="reasoning_depth",
        type="select",
        description="Chain-of-thought reasoning depth (advisory)",
        choices=["minimal", "standard", "deep"],
        default="standard",
    ),
    "speed_vs_accuracy": ProfileParameter(
        name="speed_vs_accuracy",
        type="select",
        description="Tradeoff preference — maps to router strategy hints",
        choices=["speed", "balanced", "accuracy"],
        default="balanced",
    ),
    "cost_sensitivity": ProfileParameter(
        name="cost_sensitivity",
        type="select",
        description="Budget awareness — affects router model selection hints",
        choices=["low", "medium", "high"],
        default="medium",
    ),
    "multimodal": ProfileParameter(
        name="multimodal",
        type="boolean",
        description="Require vision-enabled models when true",
        default=False,
    ),
    "json_mode": ProfileParameter(
        name="json_mode",
        type="boolean",
        description="Enforce strict JSON responses when supported",
        default=False,
    ),
    "tool_use": ProfileParameter(
        name="tool_use",
        type="boolean",
        description="Require models with function/tool calling support",
        default=False,
    ),
}


@dataclass
class Profile:
    """A named, reusable configuration bundle.

    Profiles standardize model behavior across providers by encapsulating
    common parameter sets. They can inherit from other profiles via the
    ``extends`` field.

    Attributes:
        name: Unique profile identifier (lowercase).
        description: Human-readable description.
        parameters: Parameter values (keys must exist in
            :data:`PARAMETER_DEFINITIONS`).
        tags: Tags for categorization and filtering.
        extends: Optional parent profile name for inheritance.
        source: Whether this profile is built-in or user-defined.
        notes: Optional freeform notes (author, usage context, etc.).
    """

    name: str
    description: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    extends: str | None = None
    source: Literal["builtin", "user"] = "builtin"
    notes: str | None = None

    def validate_parameters(self) -> None:
        """Validate all parameter values against :data:`PARAMETER_DEFINITIONS`.

        Checks that every key is a known parameter and that each value
        passes the corresponding :class:`ProfileParameter` validation.
        Unknown keys produce a warning-level message but do not raise.

        Raises:
            ValueError: If any parameter value fails structural validation.
        """
        import warnings

        errors: list[str] = []

        for key, value in self.parameters.items():
            param_def = PARAMETER_DEFINITIONS.get(key)
            if param_def is None:
                warnings.warn(
                    f"Unknown profile parameter '{key}' in profile "
                    f"'{self.name}'. Known parameters: "
                    f"{sorted(PARAMETER_DEFINITIONS.keys())}",
                    stacklevel=2,
                )
                continue

            try:
                # Validate and coerce in-place
                self.parameters[key] = param_def.validate(value)
            except ValueError as exc:
                errors.append(str(exc))

        if errors:
            raise ValueError(
                f"Profile '{self.name}' has invalid parameters:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the profile for API responses.

        Returns:
            A JSON-serializable dictionary with all profile metadata.
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": dict(self.parameters),
            "tags": list(self.tags),
            "extends": self.extends,
            "source": self.source,
            "notes": self.notes,
        }


def merge_parameters(
    parent: dict[str, Any],
    child: dict[str, Any],
) -> dict[str, Any]:
    """Merge parent and child profile parameters.

    Child values override parent values. Used by the registry to resolve
    ``extends`` inheritance chains.

    Args:
        parent: Parent profile's parameter dict.
        child: Child profile's parameter dict (takes precedence).

    Returns:
        A new dict with merged parameters.
    """
    return {**parent, **child}
