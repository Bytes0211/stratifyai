# Prompt Templates — StratifyAI

> **Status:** Production Ready (Phase 9.1 Complete)  
> **Version:** v0.1.4+

Reusable, parameterized prompt templates for common AI tasks. Built-in templates for code review, summarization, translation, debugging, and more.

---

## Quick Start

```python
from stratifyai.prompts import registry

# List all templates
templates = registry.list()
print(f"Found {len(templates)} templates")

# Render a template
messages = registry.render(
    "code_review",
    code="def hello(): print('world')",
    language="python",
    focus="security"
)
```

---

## Built-in Templates

| Name | Description | Tags | Parameters |
|------|-------------|------|------------|
| **code_review** | Review source code for bugs, security, and improvements | code, review | code*, language, focus |
| **summarize** | Summarize documents with configurable length and style | writing, summary | text*, max_length, style |
| **chatbot** | Conversational assistant with customizable persona | conversation, persona | persona, tone |
| **explain_concept** | Explain complex concepts at different audience levels | education, explanation | concept*, audience, depth |
| **analyze_data** | Analyze structured data (CSV, JSON, tables) | data, analysis | data*, question, format |
| **rag_synthesis** | Synthesize answers from retrieved context | rag, synthesis | context*, query* |
| **translate** | Translate text between languages with formality control | language, translation | text*, target_language*, source_language, formality |
| **debug_error** | Debug error messages and stack traces | code, debugging | error*, code, language |
| **commit_message** | Generate conventional commit messages from diffs | code, git | diff*, style |
| **api_docs** | Generate API documentation from code | code, documentation | code*, language, format |

_*Required parameters_

---

## Usage

### With ChatBuilder

```python
from stratifyai.chat import anthropic

response = await (
    anthropic
    .with_model("claude-sonnet-4-20250514")
    .with_template("code_review", code=source_code, language="python", focus="security")
    .chat("Review this code")
)
```

### With CLI

```bash
# List all templates
stratifyai templates

# Filter by tag
stratifyai templates --tag code --verbose

# Use a template
stratifyai chat \
  --template code_review \
  --params "language=python,focus=security" \
  --file script.py
```

### With API

```bash
# List templates
curl http://localhost:8080/api/templates

# Get specific template
curl http://localhost:8080/api/templates/code_review

# Render template
curl -X POST http://localhost:8080/api/templates/code_review/render \
  -H "Content-Type: application/json" \
  -d '{"params": {"code": "x=1", "language": "python"}}'
```

### Programmatic Access

```python
from stratifyai.prompts import registry

# Get template
template = registry.get("code_review")
print(template.description)
print(template.parameters)

# Render with parameters
messages = template.render(
    code="def add(a, b): return a + b",
    language="python",
    focus="style"
)

# Search templates
results = registry.search("translation")
```

---

## Creating Custom Templates

### User Directory

Create YAML files in `~/.stratifyai/prompts/`:

```yaml
# ~/.stratifyai/prompts/pr_review.yaml
name: pr_review
description: Review a GitHub pull request for our team standards
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
    description: Team coding guidelines
    default: "Follow PEP 8, use type hints, write docstrings"
    required: false

system: |
  You are a senior engineer reviewing a pull request.
  Team guidelines: {guidelines}

user: |
  Review this PR diff:
  
  ```diff
  {diff}
  ```
```

### Template Schema

```yaml
name: template_name           # Required: unique identifier
description: Template purpose  # Optional
system: System prompt {param}  # Required: can be empty
user: User prompt {param}      # Required

parameters:                    # Optional
  - name: param_name
    type: string|text|number|choice
    description: Parameter description
    default: default_value     # Makes parameter optional
    required: true|false
    choices: [opt1, opt2]     # For type: choice

tags: [tag1, tag2]            # Optional
recommended_models: [model1]  # Optional
recommended_temperature: 0.5  # Optional
```

---

## Parameter Types

| Type | Description | Validation |
|------|-------------|------------|
| `string` | Short text value | None |
| `text` | Long text (code, documents) | None |
| `number` | Numeric value | Coerces to float |
| `choice` | One of predefined values | Must be in `choices` list |

---

## Advanced Features

### Template Overriding

User templates with the same name override built-in templates:

```bash
# Override built-in code_review template
~/.stratifyai/prompts/code_review.yaml
```

### Programmatic Registration

```python
from stratifyai.prompts import PromptTemplate, PromptParameter, registry

template = PromptTemplate(
    name="custom",
    description="Custom template",
    system="You are a {role}",
    user="Task: {task}",
    parameters=[
        PromptParameter(name="role", required=True),
        PromptParameter(name="task", required=True),
    ],
    source="user"
)

registry.register(template)
```

### Temperature Auto-Configuration

Templates with `recommended_temperature` automatically configure ChatBuilder:

```python
# Template has recommended_temperature: 0.3
builder = anthropic.with_template("code_review", code=src)
# builder._temperature is now 0.3 (if not already set)
```

---

## API Reference

### `PromptTemplate`

```python
template.render(**kwargs) -> list[Message]
template.to_dict() -> dict
```

### `PromptRegistry`

```python
registry.get(name: str) -> PromptTemplate
registry.list(tag: str = None, source: str = None) -> list[PromptTemplate]
registry.render(name: str, **kwargs) -> list[Message]
registry.search(query: str) -> list[PromptTemplate]
registry.tags() -> list[str]
registry.register(template: PromptTemplate) -> None
registry.load_directory(path: Path, source: str = "user") -> int
```

---

## Security

### Safe Substitution

Templates use `str.format_map()` for parameter substitution — **no code execution**:

```python
# Safe: malicious input is treated as plain text
template.render(code="__import__('os').system('rm -rf /')")
# Renders as string literal, does NOT execute
```

### YAML Loading

All YAML parsing uses `yaml.safe_load()` exclusively.

### Path Isolation

User templates are read from `~/.stratifyai/prompts/` only. No arbitrary file paths accepted.

---

## Best Practices

1. **Name templates descriptively**: `code_review`, not `cr`
2. **Provide clear descriptions**: Help users discover relevant templates
3. **Use sensible defaults**: Make templates work with minimal parameters
4. **Tag appropriately**: Enable filtering by domain (`code`, `writing`, `data`)
5. **Test with real data**: Ensure templates work with actual use cases
6. **Document parameters**: Clear descriptions help users provide correct values

---

## Examples

### Code Review Workflow

```bash
# Review a file
stratifyai chat --template code_review --file src/app.py --params "focus=security"

# Review with specific language hint
stratifyai chat --template code_review --file script.js --params "language=javascript,focus=performance"
```

### Document Processing

```python
from stratifyai.prompts import registry
from stratifyai import LLMClient

client = LLMClient(provider="anthropic")

# Summarize document
with open("report.txt") as f:
    text = f.read()

messages = registry.render(
    "summarize",
    text=text,
    max_length=200,
    style="executive_summary"
)

response = await client.chat(model="claude-sonnet-4-20250514", messages=messages)
print(response.content)
```

### Translation Service

```python
messages = registry.render(
    "translate",
    text="Hello, how are you?",
    target_language="Spanish",
    formality="formal"
)
```

---

## Troubleshooting

**Template not found**
```python
KeyError: Template 'typo' not found. Available templates: [...]
```
Check spelling and run `stratifyai templates` to list available templates.

**Missing required parameter**
```python
ValueError: Required parameter 'code' not provided. Description: Source code to review
```
Provide all required parameters when rendering.

**Invalid choice**
```python
ValueError: Parameter 'focus' must be one of ['all', 'bugs', 'security', ...], got: 'invalid'
```
Use only allowed values from the `choices` list.

---

## Contributing Templates

Want to add a built-in template? See `catalog/README.md` for contribution guidelines.

---

## See Also

- [CLI Usage](cli-usage.md) — Full CLI reference
- [API Reference](API-REFERENCE.md) — REST API documentation
- [ChatBuilder](API-REFERENCE.md#chatbuilder) — Fluent API
- [Catalog Management](CATALOG_MANAGEMENT.md) — Model catalog
