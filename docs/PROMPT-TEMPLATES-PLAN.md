# Prompt Template Implementation Plan — StratifyAI Phase 9.1

> **Author:** AI Agent (Oz)
> **Created:** February 27, 2026
> **Status:** ✅ Complete — Validated February 28, 2026
> **Depends on:** Phase 8.3 complete; Phase 9.2 (MCP Server Core) for MCP prompt exposure (§9.1.7); standalone for library use

---

## Table of Contents

- [Executive Summary](#executive-summary)
- [Problem Statement](#problem-statement)
- [Design Goals](#design-goals)
- [Architecture](#architecture)
- [Template Catalog](#template-catalog)
- [Implementation Plan](#implementation-plan)
  - [9.1.1 — PromptTemplate Data Model](#911--prompttemplate-data-model)
  - [9.1.2 — Built-in Template Library](#912--built-in-template-library)
  - [9.1.3 — PromptRegistry (Discovery & Loading)](#913--promptregistry-discovery--loading)
  - [9.1.4 — ChatBuilder Integration](#914--chatbuilder-integration)
  - [9.1.5 — CLI Integration](#915--cli-integration)
  - [9.1.6 — API Integration](#916--api-integration)
  - [9.1.7 — MCP Prompt Exposure](#917--mcp-prompt-exposure)
  - [9.1.8 — User-Defined Templates](#918--user-defined-templates)
  - [9.1.9 — Tests](#919--tests)
  - [9.1.10 — Documentation](#9110--documentation)
- [Security Considerations](#security-considerations)
- [Template Specification](#template-specification)
- [File Manifest](#file-manifest)
- [Acceptance Criteria](#acceptance-criteria)
- [Risk Assessment](#risk-assessment)
- [Relationship to Other Plans](#relationship-to-other-plans)

---

## Executive Summary

StratifyAI has no prompt template infrastructure. System prompts and user
prompt patterns are hardcoded inline across example scripts, the CLI, and the
API. This plan introduces a `PromptTemplate` system that:

1. Defines a simple, typed data model for parameterized prompt templates
2. Ships 10+ built-in templates extracted from existing example code
3. Provides a `PromptRegistry` for discovering, loading, and listing templates
4. Integrates with the `ChatBuilder` fluent API, the CLI, the REST API, and
   the MCP server
5. Supports user-defined templates via YAML files in `~/.stratifyai/prompts/`

The system is designed to be **lightweight** (no new dependencies), **composable**
(templates produce `Message` lists that work with every existing code path),
and **MCP-native** (templates register as MCP Prompts automatically in
Phase 9.1.7).

**Estimated effort:** 2–3 days
**New code:** ~1,200–1,500 lines (library + templates + tests + docs)
**New dependencies:** None (`PyYAML` is already a transitive dependency
via multiple packages; falls back gracefully if absent)

---

## Problem Statement

### Current State

Prompts are scattered and duplicated across the codebase:

| Location | Prompt | Lines |
|----------|--------|-------|
| `examples/code_reviewer.py` | Code review system prompt | ~15 |
| `examples/document_summarizer.py` | Summarization prompt | ~10 |
| `examples/chatbot.py` | Chatbot persona prompt | ~8 |
| `examples/rag_example.py` | RAG synthesis prompt | ~12 |
| `stratifyai/rag.py` L281–288 | Hardcoded RAG synthesis prompt | ~8 |
| `cli/stratifyai_cli.py` | Interactive mode system prompt | ~5 |

### Consequences

1. **No reuse** — Each script defines its own prompts from scratch
2. **No discoverability** — Users can't browse available prompt patterns
3. **No parameterization** — Prompts are string literals, not templates
4. **No MCP exposure** — MCP clients can't discover reusable prompts
5. **No customization** — Users can't override built-in prompts
6. **Duplication** — The RAG prompt exists in both `rag.py` and `rag_example.py`

---

## Design Goals

| # | Goal | Rationale |
|---|------|-----------|
| 1 | **Zero new dependencies** | PyYAML is already transitive; `str.format_map()` for rendering |
| 2 | **Produce `Message` lists** | Templates output the same type every provider already consumes |
| 3 | **YAML-first storage** | Human-readable, diff-friendly, easy to contribute |
| 4 | **Registry with lazy loading** | Templates loaded on first access, not at import time |
| 5 | **Fluent builder integration** | `ChatBuilder.with_template()` chains naturally |
| 6 | **CLI-native** | `--template` flag and `templates` command for discovery |
| 7 | **API-native** | REST endpoints for listing, inspecting, and rendering templates |
| 8 | **MCP-native** | Templates auto-register as MCP Prompts when MCP server is present |
| 9 | **User-extensible** | YAML files in `~/.stratifyai/prompts/` override or extend built-ins |
| 10 | **Secure** | `str.format_map()` only (no `eval`/`exec`), `yaml.safe_load()` only |

---

## Architecture

### Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  YAML Files     │────▶│  PromptRegistry   │────▶│  PromptTemplate  │
│  (built-in +    │     │  (singleton)      │     │  .render(**kw)   │
│   user-defined) │     │                   │     │      │           │
└─────────────────┘     └──────────────────┘     └──────┼───────────┘
                                                        │
                                                        ▼
                                                 list[Message]
                                                        │
                         ┌──────────────────────────────┼──────────────┐
                         │              │               │              │
                         ▼              ▼               ▼              ▼
                   ChatBuilder    CLI --template   API /render    MCP Prompt
                  .with_template()   flag         endpoint        handler
```

### Key Classes

```
PromptParameter
├── name: str
├── type: "string" | "text" | "number" | "choice"
├── description: str
├── default: Any | None
├── required: bool
├── choices: list[str] | None
└── validate(value) -> Any

PromptTemplate
├── name: str
├── description: str
├── system: str                    # Template string with {param} placeholders
├── user: str                      # Template string with {param} placeholders
├── parameters: list[PromptParameter]
├── tags: list[str]
├── recommended_models: list[str]
├── recommended_temperature: float | None
├── source: "builtin" | "user"
├── render(**kwargs) -> list[Message]
└── to_dict() -> dict

PromptRegistry (singleton)
├── _templates: dict[str, PromptTemplate]
├── _loaded: bool
├── get(name) -> PromptTemplate
├── list(tag?, source?) -> list[PromptTemplate]
├── render(name, **kwargs) -> list[Message]
├── register(template) -> None
├── search(query) -> list[PromptTemplate]
├── tags() -> list[str]
└── load_directory(path) -> int
```

---

## Template Catalog

### Built-in Templates (10)

| Name | Source | Tags | Parameters |
|------|--------|------|------------|
| `code_review` | `examples/code_reviewer.py` | `code`, `review` | `code`, `language?`, `focus?` |
| `summarize` | `examples/document_summarizer.py` | `writing`, `summary` | `text`, `max_length?`, `style?` |
| `chatbot` | `examples/chatbot.py` | `conversation`, `persona` | `persona?`, `tone?` |
| `explain_concept` | New | `education`, `explanation` | `concept`, `audience?`, `depth?` |
| `analyze_data` | New | `data`, `analysis` | `data`, `question?`, `format?` |
| `rag_synthesis` | `stratifyai/rag.py` L281 | `rag`, `synthesis` | `context`, `query` |
| `translate` | New | `language`, `translation` | `text`, `target_language`, `source_language?`, `formality?` |
| `debug_error` | New | `code`, `debugging` | `error`, `code?`, `language?` |
| `commit_message` | New | `code`, `git` | `diff`, `style?` |
| `api_docs` | New | `code`, `documentation` | `code`, `language?`, `format?` |

### Template Design Principles

1. **System + User separation** — System prompt sets persona/rules; user prompt frames the task
2. **Sensible defaults** — Templates work with only required parameters
3. **Progressive detail** — Optional parameters add specificity without breaking the base prompt
4. **Model-agnostic** — Templates work across all providers; `recommended_models` is advisory
5. **Composable** — Rendered `Message` lists can be extended with additional messages

---

## Implementation Plan

### 9.1.1 — PromptTemplate Data Model

> **File:** `stratifyai/prompts/models.py` (~120–150 lines)

Define the core data model using Python dataclasses.

```python
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
```

**Key design decisions:**

1. **`str.format_map()`** — Safe string substitution (no code execution).
   Users who need literal braces use `{{` / `}}` escaping.
2. **`Message` output** — Templates produce the same type consumed by
   `ChatRequest`, `ChatBuilder`, `LLMClient`, and the MCP layer.
3. **Validation first** — All parameters are validated before any
   substitution occurs, giving clear error messages.
4. **Unknown parameter warnings** — Typos in kwargs produce a warning
   rather than a silent failure.

---

### 9.1.2 — Built-in Template Library

> **Directory:** `stratifyai/prompts/templates/` (10 YAML files, ~50–80 lines each)
> **Total:** ~600–800 lines of YAML

Each template is a standalone YAML file that maps directly to a
`PromptTemplate` dataclass.

**Example: `code_review.yaml`**

```yaml
name: code_review
description: >
  Review source code for bugs, style issues, security vulnerabilities,
  and improvement opportunities. Provides actionable, line-specific feedback.
tags:
  - code
  - review
recommended_models:
  - claude-sonnet-4-20250514
  - gpt-4.1
recommended_temperature: 0.3

parameters:
  - name: code
    type: text
    description: Source code to review
    required: true
  - name: language
    type: string
    description: Programming language (auto-detected if not specified)
    default: "auto"
    required: false
  - name: focus
    type: choice
    description: Area to focus the review on
    default: "all"
    required: false
    choices:
      - all
      - bugs
      - security
      - performance
      - style
      - maintainability

system: |
  You are an expert code reviewer specializing in {language} development.
  Focus area: {focus}.

  Guidelines:
  - Be specific: reference line numbers and variable names
  - Prioritize: critical bugs > security > performance > style
  - Be constructive: suggest fixes, not just problems
  - Use markdown formatting with code blocks for suggestions
  - If language is "auto", detect the language from the code

user: |
  Review the following code:

  ```
  {code}
  ```
```

**Example: `summarize.yaml`**

```yaml
name: summarize
description: >
  Summarize a document or text passage with configurable length and style.
  Supports bullet points, narrative, and executive summary formats.
tags:
  - writing
  - summary
recommended_models:
  - claude-sonnet-4-20250514
  - gpt-4.1-mini
recommended_temperature: 0.3

parameters:
  - name: text
    type: text
    description: Document text to summarize
    required: true
  - name: max_length
    type: number
    description: Maximum summary length in words
    default: 200
    required: false
  - name: style
    type: choice
    description: Summary output style
    default: "bullet_points"
    required: false
    choices:
      - bullet_points
      - narrative
      - executive_summary
      - one_sentence

system: |
  You are a professional document summarizer. Your summaries are:
  - Accurate: preserve key facts and conclusions
  - Concise: stay within {max_length} words
  - Complete: cover all major themes
  - Well-structured: use the "{style}" format

  Style guidelines:
  - bullet_points: use markdown bullet lists with bold topic labels
  - narrative: flowing prose paragraphs
  - executive_summary: opening statement, key findings, recommendations
  - one_sentence: single comprehensive sentence

user: |
  Summarize the following text in {style} format (max {max_length} words):

  {text}
```

**Remaining 8 templates** follow the same pattern:

| Template | Key System Prompt Focus | Key User Prompt Structure |
|----------|------------------------|--------------------------|
| `chatbot` | Persona definition (`{persona}`, `{tone}`) | Open-ended conversation starter |
| `explain_concept` | Educational explanation (`{audience}`, `{depth}`) | "Explain {concept}" |
| `analyze_data` | Data analysis expert (`{format}`) | "Analyze: {data}. Question: {question}" |
| `rag_synthesis` | Source-grounded answerer | "Sources: {context}. Question: {query}" |
| `translate` | Translation expert (`{formality}`) | "Translate to {target_language}: {text}" |
| `debug_error` | Debugging assistant (`{language}`) | "Error: {error}. Code: {code}" |
| `commit_message` | Conventional commit expert (`{style}`) | "Diff: {diff}" |
| `api_docs` | Technical writer (`{format}`) | "Document: {code}" |

---

### 9.1.3 — PromptRegistry (Discovery & Loading)

> **File:** `stratifyai/prompts/registry.py` (~180–220 lines)

The `PromptRegistry` is a singleton that discovers, loads, and indexes
templates from both built-in and user directories.

```python
"""Prompt template registry for discovery and loading."""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Any, Optional

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

    def load_directory(
        self, path: Path, source: str = "user"
    ) -> int:
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
                logger.warning(
                    "Failed to load template %s: %s", yaml_path.name, exc
                )
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
                f"Template '{name}' not found. "
                f"Available templates: {available}"
            )
        return self._templates[name]

    def list(
        self,
        tag: Optional[str] = None,
        source: Optional[str] = None,
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


def _load_yaml_template(
    path: Path, source: str = "user"
) -> PromptTemplate:
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
    except ImportError:
        raise ImportError(
            "PyYAML is required to load YAML templates. "
            "Install it with: pip install pyyaml"
        )

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path.name}")

    for required_field in ("name", "system", "user"):
        if required_field not in data:
            raise ValueError(
                f"Template {path.name} missing required field: "
                f"'{required_field}'"
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
```

**Package init (`stratifyai/prompts/__init__.py`):**

```python
"""Prompt template system for StratifyAI."""

from stratifyai.prompts.models import PromptParameter, PromptTemplate
from stratifyai.prompts.registry import PromptRegistry

# Singleton registry instance
registry = PromptRegistry()

__all__ = [
    "PromptParameter",
    "PromptTemplate",
    "PromptRegistry",
    "registry",
]
```

---

### 9.1.4 — ChatBuilder Integration

> **File:** `stratifyai/chat/builder.py` (~30 lines added)

Add a `with_template()` method to `ChatBuilder` that loads a template,
renders it, and configures the builder with the resulting system prompt
and user message.

```python
def with_template(
    self, name: str, **params: Any
) -> "ChatBuilder":
    """Configure the builder using a named prompt template.

    Loads the template from the registry, renders it with the given
    parameters, and applies the resulting system/user prompts to
    the builder.

    If the template specifies a ``recommended_temperature`` and no
    temperature has been set on this builder, the recommended value
    is applied automatically.

    Args:
        name: Template name (e.g., ``"code_review"``).
        **params: Template parameter values.

    Returns:
        A new ``ChatBuilder`` with the template applied.

    Raises:
        KeyError: If the template is not found.
        ValueError: If required template parameters are missing.

    Example::

        response = await (
            anthropic
            .with_model("claude-sonnet-4-20250514")
            .with_template("code_review", code=src, language="python")
            .chat("Review this code")
        )
    """
    from stratifyai.prompts import registry

    template = registry.get(name)
    messages = template.render(**params)

    # Extract system and user content from rendered messages
    system_content = None
    user_content = None
    for msg in messages:
        if msg.role == "system":
            system_content = msg.content
        elif msg.role == "user":
            user_content = msg.content

    updates = {}
    if system_content:
        updates["_system"] = system_content
    if user_content:
        updates["_template_user"] = user_content

    # Apply recommended temperature if none is set
    if (
        template.recommended_temperature is not None
        and self._temperature is None
    ):
        updates["_temperature"] = template.recommended_temperature

    return self._clone(**updates)
```

The `_build_messages()` method (internal) is updated to prepend the
template's user message if present:

```python
def _build_messages(self, user_prompt: str) -> list["Message"]:
    """Build the final message list for a chat request.

    If a template was applied via ``with_template()``, the template's
    rendered user message replaces the ``user_prompt`` argument.
    """
    from stratifyai.models import Message

    messages: list[Message] = []

    # System prompt
    combined_system = ""
    if self._developer:
        combined_system += self._developer + "\n\n"
    if self._system:
        combined_system += self._system
    if combined_system.strip():
        messages.append(Message(role="system", content=combined_system.strip()))

    # User message: template user content takes priority if set,
    # but the explicit user_prompt is always appended
    template_user = getattr(self, "_template_user", None)
    if template_user:
        messages.append(Message(role="user", content=template_user))
        if user_prompt and user_prompt.strip():
            messages.append(Message(role="user", content=user_prompt))
    else:
        messages.append(Message(role="user", content=user_prompt))

    return messages
```

---

### 9.1.5 — CLI Integration

> **File:** `cli/stratifyai_cli.py` (~80–100 lines added)

**New `--template` and `--params` flags on the `chat` command:**

```python
@app.command()
def chat(
    text: str = typer.Option(..., "--text", "-t"),
    provider: str = typer.Option("openai", "--provider", "-p"),
    model: str = typer.Option("gpt-4.1-mini", "--model", "-m"),
    template: Optional[str] = typer.Option(
        None, "--template", help="Prompt template name (e.g. code_review)"
    ),
    params: Optional[str] = typer.Option(
        None, "--params", help='Template params as key=value pairs, comma-separated'
    ),
    ...
):
```

When `--template` is provided:

1. Load the template from the registry
2. Parse `--params` into a dictionary (`"language=python,focus=security"` → `{"language": "python", "focus": "security"}`)
3. If `--file` is also provided, inject the file content as the first required text parameter
4. Render the template and use the resulting messages

**New `templates` command:**

```python
@app.command()
def templates(
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show parameters"),
):
    """List available prompt templates."""
    from stratifyai.prompts import registry

    template_list = registry.list(tag=tag)

    table = Table(title="📋 Prompt Templates", show_lines=True)
    table.add_column("Name", style="cyan bold")
    table.add_column("Description", style="white")
    table.add_column("Tags", style="yellow")
    table.add_column("Source", style="green")

    if verbose:
        table.add_column("Parameters", style="magenta")

    for t in template_list:
        row = [
            t.name,
            t.description[:80] + "..." if len(t.description) > 80 else t.description,
            ", ".join(t.tags),
            t.source,
        ]
        if verbose:
            param_strs = []
            for p in t.parameters:
                marker = "*" if p.required else ""
                default_str = f"={p.default}" if p.default is not None else ""
                param_strs.append(f"{p.name}{marker}{default_str}")
            row.append(", ".join(param_strs))
        table.add_row(*row)

    console.print(table)
    console.print(f"\n[dim]{len(template_list)} templates found[/dim]")
```

---

### 9.1.6 — API Integration

> **File:** `api/main.py` (~40–60 lines added)

Three new REST endpoints:

```python
@app.get("/api/templates")
async def list_templates(
    tag: Optional[str] = None,
    source: Optional[str] = None,
):
    """List all available prompt templates."""
    from stratifyai.prompts import registry
    templates = registry.list(tag=tag, source=source)
    return [t.to_dict() for t in templates]


@app.get("/api/templates/{name}")
async def get_template(name: str):
    """Get a specific template by name."""
    from stratifyai.prompts import registry
    try:
        template = registry.get(name)
        return template.to_dict()
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/templates/{name}/render")
async def render_template(
    name: str,
    params: dict,
):
    """Render a template with parameters and return message list."""
    from stratifyai.prompts import registry
    try:
        template = registry.get(name)
        messages = template.render(**params)
        return [{"role": m.role, "content": m.content} for m in messages]
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
```

The existing `ChatCompletionRequest` model is extended to accept an
optional template:

```python
class ChatCompletionRequest(BaseModel):
    provider: str
    model: str
    messages: list[dict]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    template: Optional[str] = None        # NEW
    template_params: Optional[dict] = None  # NEW
```

When `template` is set, the backend renders the template and prepends
the resulting messages before the user-supplied `messages` list.

---

### 9.1.7 — MCP Prompt Exposure

> **File:** `stratifyai/mcp_server.py` (~40–60 lines added)
> **Depends on:** Phase 9.2 (MCP server exists)

Register every template from the registry as an MCP Prompt:

```python
from stratifyai.prompts import registry as prompt_registry


def register_mcp_prompts(mcp_server: FastMCP) -> None:
    """Register all prompt templates as MCP Prompts."""
    for template in prompt_registry.list():
        # Build the MCP prompt function dynamically
        _register_one_prompt(mcp_server, template)


def _register_one_prompt(mcp_server: FastMCP, template: PromptTemplate) -> None:
    """Register a single PromptTemplate as an MCP Prompt."""
    # MCP prompts return list[dict] with role/content
    param_names = [p.name for p in template.parameters]

    @mcp_server.prompt(name=template.name, description=template.description)
    async def prompt_handler(**kwargs) -> list[dict]:
        messages = template.render(**kwargs)
        return [{"role": m.role, "content": m.content} for m in messages]

    # Note: the MCP SDK infers parameter schemas from the function signature.
    # For dynamic registration, we may need to set __annotations__ on the
    # handler function to match the template's parameters.
```

MCP clients (Claude Desktop, Cursor, etc.) can then discover and use
StratifyAI's prompt templates through the standard MCP prompt protocol.

**Implementation note:** Dynamic MCP prompt registration with variable
parameter schemas requires careful handling of the `FastMCP` decorator's
introspection. If the SDK doesn't support fully dynamic signatures, fall
back to registering each prompt with a single `params: dict` parameter
and documenting the expected keys in the description.

---

### 9.1.8 — User-Defined Templates

> **Directory:** `~/.stratifyai/prompts/` (user-managed)

Users create YAML files in `~/.stratifyai/prompts/` using the same
format as built-in templates. The registry automatically discovers them.

**Override behavior:** If a user template has the same `name` as a
built-in, the user template wins. The `source` field distinguishes them
in listings.

**Example: `~/.stratifyai/prompts/pr_review.yaml`**

```yaml
name: pr_review
description: Review a GitHub pull request for our team's standards
tags:
  - code
  - review
  - team
recommended_temperature: 0.3

parameters:
  - name: diff
    type: text
    description: The PR diff content
    required: true
  - name: guidelines
    type: string
    description: Team coding guidelines to enforce
    default: "Follow PEP 8, use type hints, write docstrings"
    required: false

system: |
  You are a senior engineer reviewing a pull request.
  Team guidelines: {guidelines}

  Review criteria:
  - Correctness and edge cases
  - Adherence to team guidelines
  - Test coverage gaps
  - Security implications

user: |
  Review this PR diff:

  ```diff
  {diff}
  ```
```

**Discovery mechanism:**

1. On first registry access, `_ensure_loaded()` runs
2. Built-in templates are loaded first from `stratifyai/prompts/templates/`
3. User templates are loaded from `~/.stratifyai/prompts/` (if it exists)
4. User templates with the same name overwrite built-in entries
5. A `source` field tracks provenance ("builtin" vs "user")

---

### 9.1.9 — Tests

> **File:** `tests/test_prompts.py` (~250–300 lines)

| Test | Validates |
|------|-----------|
| **Model tests** | |
| `test_prompt_parameter_validate_required` | Required param without value raises `ValueError` |
| `test_prompt_parameter_validate_default` | Missing param uses default |
| `test_prompt_parameter_validate_choice` | Invalid choice raises `ValueError` |
| `test_prompt_parameter_validate_number` | Number coercion works, non-numeric raises |
| `test_prompt_template_render_basic` | Renders system + user messages |
| `test_prompt_template_render_missing_required` | Raises `ValueError` |
| `test_prompt_template_render_with_defaults` | Defaults substituted correctly |
| `test_prompt_template_render_unknown_param_warns` | Warns on unknown kwargs |
| `test_prompt_template_to_dict` | Serializes correctly for API |
| **Registry tests** | |
| `test_registry_loads_builtin_templates` | Built-in templates discovered |
| `test_registry_get_existing` | Returns correct template |
| `test_registry_get_nonexistent` | Raises `KeyError` with available list |
| `test_registry_list_all` | Returns all templates |
| `test_registry_list_by_tag` | Filters by tag correctly |
| `test_registry_list_by_source` | Filters built-in vs user |
| `test_registry_render_shortcut` | `render()` combines get + render |
| `test_registry_search` | Finds by name, description, tags |
| `test_registry_tags` | Returns unique sorted tags |
| `test_registry_register_programmatic` | Manual registration works |
| `test_registry_load_user_directory` | Loads YAML from custom path |
| `test_registry_user_overrides_builtin` | User template wins on name collision |
| **YAML loading tests** | |
| `test_load_yaml_template_valid` | Parses all fields correctly |
| `test_load_yaml_template_minimal` | Handles optional fields |
| `test_load_yaml_template_invalid` | Graceful error on bad YAML |
| **Integration tests** | |
| `test_template_messages_work_with_chat_request` | Rendered messages create valid `ChatRequest` |
| `test_code_review_template_renders` | Built-in template renders with real params |
| `test_summarize_template_renders` | Built-in template renders with real params |
| `test_all_builtin_templates_render_with_defaults` | Every template renders when only defaults used |

**Test count target:** 25–30 new tests

---

### 9.1.10 — Documentation

> **Files:** `docs/PROMPT-TEMPLATES.md` (new, ~200 lines), `AGENTS.md` (update)

**`docs/PROMPT-TEMPLATES.md`** covers:

1. **Quick start** — render a template in 3 lines of code
2. **Available templates** — table of all built-in templates with
   descriptions and parameter lists
3. **Using with ChatBuilder** — `with_template()` fluent examples
4. **Using with CLI** — `--template` flag and `templates` command
5. **Using with API** — `/api/templates` endpoint examples
6. **Using with MCP** — how templates appear in Claude Desktop / Cursor
7. **Creating custom templates** — YAML format, `~/.stratifyai/prompts/`,
   override behavior
8. **Template YAML schema reference** — all supported fields

**`AGENTS.md` updates:**

- Add `stratifyai/prompts/` directory to project structure tree
- Add `tests/test_prompts.py` to test list
- Add template-related exports to the package exports section
- Update phase status

**`stratifyai/__init__.py` updates:**

```python
from .prompts import PromptTemplate, PromptParameter, PromptRegistry, registry
```

Add to `__all__`:
```python
"PromptTemplate",
"PromptParameter",
"PromptRegistry",
```

---

## Security Considerations

### Template Injection

Templates use `str.format_map()` which is **not** vulnerable to code
injection. Unlike `eval()`, `exec()`, or even `str.format()` with
attribute access (`{obj.__class__}`), `format_map()` with a plain
`dict` only performs key lookups — no attribute access, no method
calls, no expression evaluation.

**Safe:**
```python
"{code}".format_map({"code": "__import__('os').system('rm -rf /')"})
# Returns the string literally — does NOT execute it
```

### YAML Loading

All YAML loading uses `yaml.safe_load()` exclusively. The `yaml.load()`
function (which can execute arbitrary Python) is **never** used.

### User Template Directory

The user template directory (`~/.stratifyai/prompts/`) is:
- Only read, never written to by StratifyAI
- Created by the user manually
- Scoped to the user's home directory

### Path Traversal

Template loading only reads `.yaml`/`.yml` files from explicitly
configured directories using `Path.glob()`. No user-supplied paths
are used for file loading (template names are lookup keys, not
file paths).

---

## Template Specification

### YAML Schema

Each template YAML file must contain:

```yaml
# Required fields
name: string              # Unique template name (lowercase, underscore-separated)
system: string            # System prompt template with {param} placeholders
user: string              # User prompt template with {param} placeholders

# Optional fields
description: string       # Human-readable description
parameters:               # List of parameter definitions
  - name: string          #   Parameter name (matches {placeholder})
    type: string          #   "string" | "text" | "number" | "choice"
    description: string   #   Human-readable description
    default: any          #   Default value (makes param optional)
    required: boolean     #   Whether param must be provided (default: true)
    choices: list[string] #   Valid values when type is "choice"
tags: list[string]        # Categorization tags
recommended_models: list[string]  # Advisory model suggestions
recommended_temperature: number   # Advisory temperature (0.0–2.0)
```

### Type Definitions

| Type | Python Coercion | Validation |
|------|----------------|------------|
| `string` | `str(value)` | None |
| `text` | `str(value)` | None (alias for long strings) |
| `number` | `float(value)` | Must be numeric |
| `choice` | `str(value)` | Must be in `choices` list |

### Naming Conventions

- Template names: lowercase, underscore-separated (e.g., `code_review`)
- Parameter names: lowercase, underscore-separated (e.g., `max_length`)
- Tags: lowercase, single word preferred (e.g., `code`, `writing`)

---

## File Manifest

| Action | File | Lines (est.) | Description |
|--------|------|-------------|-------------|
| Created | `stratifyai/prompts/__init__.py` | 15 | Package exports + singleton registry |
| Created | `stratifyai/prompts/models.py` | 120–150 | `PromptTemplate`, `PromptParameter` |
| Created | `stratifyai/prompts/registry.py` | 180–220 | `PromptRegistry`, YAML loader |
| Created | `stratifyai/prompts/templates/code_review.yaml` | 55 | Code review template |
| Created | `stratifyai/prompts/templates/summarize.yaml` | 50 | Summarization template |
| Created | `stratifyai/prompts/templates/chatbot.yaml` | 40 | Chatbot persona template |
| Created | `stratifyai/prompts/templates/explain_concept.yaml` | 50 | Concept explanation template |
| Created | `stratifyai/prompts/templates/analyze_data.yaml` | 50 | Data analysis template |
| Created | `stratifyai/prompts/templates/rag_synthesis.yaml` | 40 | RAG synthesis template |
| Created | `stratifyai/prompts/templates/translate.yaml` | 45 | Translation template |
| Created | `stratifyai/prompts/templates/debug_error.yaml` | 50 | Error debugging template |
| Created | `stratifyai/prompts/templates/commit_message.yaml` | 45 | Git commit message template |
| Created | `stratifyai/prompts/templates/api_docs.yaml` | 50 | API documentation template |
| Created | `tests/test_prompts.py` | 250–300 | Template system tests |
| Created | `docs/PROMPT-TEMPLATES.md` | 200 | Usage documentation |
| Modified | `stratifyai/chat/builder.py` | +30 | `with_template()` method |
| Modified | `cli/stratifyai_cli.py` | +80–100 | `--template` flag, `templates` cmd |
| Modified | `api/main.py` | +40–60 | Template endpoints |
| Modified | `stratifyai/__init__.py` | +5 | New exports |
| Modified | `AGENTS.md` | +15 | Project structure + phase status |
| Modified | `docs/developer-journal.md` | +20 | Completion entry |
| Modified | `stratifyai/mcp_server.py` | +40–60 | MCP prompt registration (Phase 9.1.7) |

**Total new code:** ~1,200–1,500 lines
**New dependencies:** None (`PyYAML` is already a transitive dependency)

---

## Acceptance Criteria

- [x] All existing tests pass (378+) — 408 passed, 4 skipped
- [x] 25–30 new prompt template tests pass — 30 tests, 100% passing
- [x] All 10 built-in templates render successfully with default parameters
- [x] `from stratifyai.prompts import registry; registry.list()` returns 10 templates
- [x] `registry.render("code_review", code="x=1")` returns `list[Message]`
- [x] `ChatBuilder.with_template("code_review", code=src).chat(...)` works end-to-end
- [x] `stratifyai templates` CLI command lists all templates in a Rich table
- [x] `stratifyai chat --template code_review --params "language=python" --file code.py` works
- [x] `GET /api/templates` returns template list with parameters
- [x] `POST /api/templates/code_review/render` returns rendered messages
- [x] User templates in `~/.stratifyai/prompts/` are discovered and listed
- [x] User template overrides built-in with same name
- [x] Invalid parameters raise clear `ValueError` with parameter info
- [x] No new `ruff` or `mypy` errors introduced
- [x] `AGENTS.md`, developer journal, and docs updated
- [x] `str.format_map()` used for substitution (no `eval`, no `exec`)
- [x] YAML loaded with `safe_load()` only

> **Validation note:** One bug was found and fixed during review — the
> `TemplateRenderRequest` Pydantic model in `api/main.py` used lowercase
> `any` (built-in function) instead of `Any` (typing class), causing a
> `PydanticSchemaGenerationError` in 27 tests. Fixed by changing
> `Dict[str, any]` → `Dict[str, Any]` and adding `Any` to the typing import.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| PyYAML not available | Low | Medium | Already transitive dep; add clear error message on import failure |
| Template parameter naming collisions | Low | Low | Validate at load time; warn on duplicate names |
| User creates template that shadows critical built-in | Medium | Low | Show `source` column in listings; document override behavior |
| `str.format_map` can't handle nested braces | Low | Medium | Document escaping (`{{` / `}}`); validate templates at load time |
| Large template files slow down registry loading | Low | Low | Lazy loading already implemented; templates are tiny YAML files |
| MCP dynamic prompt registration limitations | Medium | Low | Fall back to single `params: dict` argument if SDK can't introspect |

---

## Relationship to Other Plans

- **MCP Implementation Plan (Phases 9.2–9.4):** Phase 9.1.7 of this plan is the
  same work as Phase 9.3.2 in the MCP plan. They should be implemented
  together. The MCP plan provides the server infrastructure; this plan
  provides the templates that get exposed through it. Prompt Templates
  (Phase 9.1) are implemented before MCP (Phase 9.2+) because the core
  template library is standalone and provides immediate value to the CLI,
  API, and ChatBuilder without requiring MCP infrastructure.

- **ChatBuilder (Phase 7.8):** `with_template()` extends the existing
  builder pattern without breaking any existing API. Templates are an
  optional layer — all existing `with_system()` / `with_developer()`
  usage continues to work unchanged.

- **RAG Pipeline:** The `rag_synthesis` template replaces the hardcoded
  prompt in `rag.py` L281. After this plan, `RAGClient.query()` can
  optionally accept a template name to customize the synthesis behavior.