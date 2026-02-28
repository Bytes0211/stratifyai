"""Prompt template data models."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from stratifyai.models import Message


@dataclass
class PromptParameter:
    """A single parameter in a prompt template.

    Attributes:
        name: Parameter name (used as placeholder key in template strings).
        type: Parameter type for validation and UI hints.
        description: Human-readable description for docs and MCP exposure.
        default: Default value if not provided. ``None`` means required.
        required: Whether this parameter must be supplied.
        choices: Valid choices when ``type`` is ``"choice"``.
    """

    name: str
    type: Literal["string", "text", "number", "choice"] = "string"
    description: str = ""
    default: Any = None
    required: bool = True
    choices: Optional[list[str]] = None

    def validate(self, value: Any = None) -> Any:
        """Validate and coerce a parameter value.

        Args:
            value: The value to validate. If ``None``, falls back to
                ``self.default``.

        Returns:
            The validated (and possibly coerced) value.

        Raises:
            ValueError: If a required parameter is missing, an invalid
                choice is provided, or a number cannot be coerced.
        """
        if value is None:
            value = self.default

        if value is None and self.required:
            raise ValueError(
                f"Required parameter '{self.name}' not provided. "
                f"Description: {self.description}"
            )

        if value is None:
            return value

        if self.type == "number":
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValueError(
                    f"Parameter '{self.name}' must be a number, got: {value!r}"
                )

        if self.type == "choice" and self.choices:
            if str(value) not in self.choices:
                raise ValueError(
                    f"Parameter '{self.name}' must be one of "
                    f"{self.choices}, got: {value!r}"
                )

        return value


@dataclass
class PromptTemplate:
    """A parameterized prompt template that renders to a list of Messages.

    Attributes:
        name: Unique template name (lowercase, underscore-separated).
        description: Human-readable description for discovery.
        system: System prompt template string with ``{param}`` placeholders.
        user: User prompt template string with ``{param}`` placeholders.
        parameters: List of parameter definitions.
        tags: Tags for categorization and filtering.
        recommended_models: Advisory list of models suited for this template.
        recommended_temperature: Advisory temperature setting.
        source: Whether this template is built-in or user-defined.
    """

    name: str
    description: str
    system: str
    user: str
    parameters: list[PromptParameter] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    recommended_models: list[str] = field(default_factory=list)
    recommended_temperature: Optional[float] = None
    source: Literal["builtin", "user"] = "builtin"

    def render(self, **kwargs: Any) -> list[Message]:
        """Render the template with the given parameters.

        Validates all parameters, substitutes placeholders using
        ``str.format_map()``, and returns a list of ``Message`` objects.

        Args:
            **kwargs: Parameter values keyed by parameter name.

        Returns:
            A list of ``Message`` objects (system + user).

        Raises:
            ValueError: If required parameters are missing or invalid.
        """
        # Warn on unknown parameters
        known_names = {p.name for p in self.parameters}
        for key in kwargs:
            if key not in known_names:
                warnings.warn(
                    f"Unknown parameter '{key}' for template '{self.name}'. "
                    f"Known parameters: {sorted(known_names)}",
                    stacklevel=2,
                )

        # Validate and collect final values
        values: dict[str, Any] = {}
        for param in self.parameters:
            raw = kwargs.get(param.name)
            values[param.name] = param.validate(raw)

        # Render templates using str.format_map (safe — no eval/exec)
        rendered_system = self.system.format_map(values)
        rendered_user = self.user.format_map(values)

        messages: list[Message] = []
        if rendered_system.strip():
            messages.append(Message(role="system", content=rendered_system))
        messages.append(Message(role="user", content=rendered_user))
        return messages

    def to_dict(self) -> dict:
        """Serialize the template for API responses.

        Returns:
            A JSON-serializable dictionary with all template metadata.
        """
        return {
            "name": self.name,
            "description": self.description,
            "system": self.system,
            "user": self.user,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "description": p.description,
                    "default": p.default,
                    "required": p.required,
                    "choices": p.choices,
                }
                for p in self.parameters
            ],
            "tags": self.tags,
            "recommended_models": self.recommended_models,
            "recommended_temperature": self.recommended_temperature,
            "source": self.source,
        }
