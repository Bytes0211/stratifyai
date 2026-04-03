"""Prompt template registry for discovery and loading."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from stratifyai.models import Message
from stratifyai.prompts.models import PromptParameter, PromptTemplate

logger = logging.getLogger(__name__)

# Directories
_BUILTIN_DIR = Path(__file__).parent / "templates"
_USER_DIR = Path.home() / ".stratifyai" / "prompts"


class PromptRegistry:
    """Singleton registry for discovering, loading, and rendering templates.

    Templates are loaded lazily on first access. Built-in templates are
    loaded from ``stratifyai/prompts/templates/``. User templates from
    ``~/.stratifyai/prompts/`` override built-ins with the same name.

    Usage::

        from stratifyai.prompts import registry

        # List all templates
        for t in registry.list():
            print(t.name, t.description)

        # Render a template
        messages = registry.render("code_review", code="x = 1")
    """

    def __init__(self) -> None:
        self._templates: dict[str, PromptTemplate] = {}
        self._loaded: bool = False

    def _ensure_loaded(self) -> None:
        """Load templates on first access (lazy)."""
        if self._loaded:
            return
        self._loaded = True
        self.load_directory(_BUILTIN_DIR, source="builtin")
        if _USER_DIR.is_dir():
            self.load_directory(_USER_DIR, source="user")

    def load_directory(self, path: Path, source: str = "user") -> int:
        """Load all YAML templates from a directory.

        Args:
            path: Directory containing ``.yaml`` / ``.yml`` files.
            source: Label for the source ("builtin" or "user").

        Returns:
            Number of templates successfully loaded.
        """
        count = 0
        if not path.is_dir():
            return count

        for yaml_path in sorted(path.glob("*.y*ml")):
            try:
                template = _load_yaml_template(yaml_path, source=source)
                self._templates[template.name] = template
                count += 1
            except Exception as exc:
                logger.warning("Failed to load template %s: %s", yaml_path.name, exc)
        return count

    def register(self, template: PromptTemplate) -> None:
        """Register a template programmatically."""
        self._ensure_loaded()
        self._templates[template.name] = template

    def get(self, name: str) -> PromptTemplate:
        """Get a template by name.

        Args:
            name: The template name.

        Returns:
            The ``PromptTemplate`` instance.

        Raises:
            KeyError: If the template is not found (message lists available
                templates).
        """
        self._ensure_loaded()
        if name not in self._templates:
            available = sorted(self._templates.keys())
            raise KeyError(
                f"Template '{name}' not found. Available templates: {available}"
            )
        return self._templates[name]

    def list(
        self,
        tag: str | None = None,
        source: str | None = None,
    ) -> list[PromptTemplate]:
        """List templates with optional filtering.

        Args:
            tag: Filter by tag (e.g., ``"code"``).
            source: Filter by source (``"builtin"`` or ``"user"``).

        Returns:
            List of matching templates, sorted by name.
        """
        self._ensure_loaded()
        templates = list(self._templates.values())

        if tag:
            templates = [t for t in templates if tag in t.tags]
        if source:
            templates = [t for t in templates if t.source == source]

        return sorted(templates, key=lambda t: t.name)

    def render(self, name: str, **kwargs: Any) -> list[Message]:
        """Shortcut: get a template and render it in one call.

        Args:
            name: Template name.
            **kwargs: Template parameter values.

        Returns:
            List of rendered ``Message`` objects.
        """
        template = self.get(name)
        return template.render(**kwargs)

    def tags(self) -> list[str]:
        """Return all unique tags across all templates, sorted."""
        self._ensure_loaded()
        all_tags: set[str] = set()
        for t in self._templates.values():
            all_tags.update(t.tags)
        return sorted(all_tags)

    def search(self, query: str) -> list[PromptTemplate]:
        """Search templates by name, description, and tags.

        Args:
            query: Case-insensitive search string.

        Returns:
            Matching templates sorted by name.
        """
        self._ensure_loaded()
        q = query.lower()
        results = []
        for t in self._templates.values():
            if (
                q in t.name.lower()
                or q in t.description.lower()
                or any(q in tag.lower() for tag in t.tags)
            ):
                results.append(t)
        return sorted(results, key=lambda t: t.name)


def _load_yaml_template(path: Path, source: str = "user") -> PromptTemplate:
    """Load a single YAML file into a PromptTemplate.

    Args:
        path: Path to the ``.yaml`` file.
        source: Source label (``"builtin"`` or ``"user"``).

    Returns:
        A ``PromptTemplate`` instance.

    Raises:
        ImportError: If PyYAML is not installed.
        ValueError: If the YAML is missing required fields.
    """
    try:
        import yaml
    except ImportError as e:
        raise ImportError(
            "PyYAML is required to load YAML templates. "
            "Install it with: pip install pyyaml"
        ) from e

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path.name}")

    for required_field in ("name", "system", "user"):
        if required_field not in data:
            raise ValueError(
                f"Template {path.name} missing required field: '{required_field}'"
            )

    parameters = []
    for p in data.get("parameters", []):
        parameters.append(
            PromptParameter(
                name=p["name"],
                type=p.get("type", "string"),
                description=p.get("description", ""),
                default=p.get("default"),
                required=p.get("required", True),
                choices=p.get("choices"),
            )
        )

    return PromptTemplate(
        name=data["name"],
        description=data.get("description", ""),
        system=data["system"],
        user=data["user"],
        parameters=parameters,
        tags=data.get("tags", []),
        recommended_models=data.get("recommended_models", []),
        recommended_temperature=data.get("recommended_temperature"),
        source=source,
    )
