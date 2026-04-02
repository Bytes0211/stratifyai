# StratifyAI Profile System User Guide

*Status: Draft — Phase 9 (Profiles) In Progress*  
*Last Updated: February 28, 2026*

---

## 1. Overview

Profiles provide reusable configuration bundles that standardize StratifyAI’s behavior across providers and models.  
They encapsulate common parameter sets (temperature, max tokens, reasoning depth, JSON enforcement, tool usage, etc.) so that teams can:

- Reuse consistent settings across projects.
- Avoid manual reconfiguration whenever the underlying provider or model changes.
- Enforce policy-driven defaults (e.g., “cheap”, “reasoning”, “vision”).

Profiles are complementary to prompt templates. Templates control *what* the AI should say; profiles control *how* the AI should behave.

---

## 2. Quick Start Workflow

1. **List available profiles**  
   ```bash
   stratifyai profiles
   ```

2. **Run the CLI with a profile**  
   ```bash
   stratifyai chat --profile reasoning --message "Explain quantum entanglement."
   ```

3. **Apply a profile in Python**  
   ```python
   from stratifyai.chat import openai

   response = (
       openai
       .with_model("gpt-4.1")
       .with_profile("balanced")
       .chat_sync("Summarize the latest climate research.")
   )
   ```

4. **Inspect a profile via API**  
   ```bash
   curl -H "Authorization: Bearer $STRATIFYAI_API_KEY" \
        http://localhost:8080/api/profiles/reasoning
   ```

5. **Create or override a profile**  
   - Copy the built-in YAML structure (see Section 4) into `~/.stratifyai/profiles/my_profile.yaml`.
   - Reload or restart your application; the registry picks up changes on next access.

---

## 3. Profile Capabilities

| Capability           | Description                                             |
|----------------------|---------------------------------------------------------|
| Temperature control  | Manage creativity/variance across providers.            |
| Max tokens           | Set consistent output length budgets.                   |
| Reasoning depth      | Encourage minimal/standard/deep reasoning.              |
| Speed vs. accuracy   | Hint the router to favor latency, balance, or quality.  |
| Cost sensitivity     | Steer model selection toward low-cost options.          |
| Multimodal toggle    | Require vision-enabled models when true.                |
| JSON mode            | Enforce strict JSON responses when supported.           |
| Tool availability    | Ensure models support function/tool calling.            |

Profiles also map router hints automatically:
- `speed` → latency strategy  
- `balanced` → hybrid strategy  
- `accuracy` or high cost sensitivity → quality strategy

---

## 4. Profile YAML Schema

Profiles are defined in YAML files either bundled with the package or stored in `~/.stratifyai/profiles/`.  
Each file may contain one or more profiles. Example:

```yaml
profiles:
  - name: reasoning
    description: >
      Deep reasoning profile for high-accuracy tasks.
    extends: balanced
    parameters:
      temperature: 0.2
      max_tokens: 4000
      reasoning_depth: deep
      speed_vs_accuracy: accuracy
      cost_sensitivity: high
      json_mode: false
      tool_use: true
    tags: [reasoning, analysis]
```

### Required fields
- `name`: Unique identifier (lowercase, kebab or snake case recommended).
- `description`: Human-readable summary.
- `parameters`: Key/value map (see Section 5).
- Optional: `extends` (inherit from another profile), `tags`, `notes`.

---

## 5. Supported Parameters

| Parameter          | Type     | Default | Notes                                                                 |
|--------------------|----------|---------|-----------------------------------------------------------------------|
| `temperature`      | number   | 0.7     | Range 0.0–2.0, provider limits enforced.                              |
| `max_tokens`       | integer  | derives | Clamped to provider/model `api_max_input` where available.            |
| `reasoning_depth`  | string   | standard| One of `minimal`, `standard`, `deep` (advisory).                      |
| `speed_vs_accuracy`| string   | balanced| Maps to routing strategy (`speed`, `balanced`, `accuracy`).           |
| `cost_sensitivity` | string   | medium  | Values: `low`, `medium`, `high` (affects router hints).               |
| `multimodal`       | boolean  | false   | Requires models with `supports_vision = true`.                        |
| `json_mode`        | boolean  | false   | Restricts to models supporting strict JSON mode.                      |
| `tool_use`         | boolean  | true/false| Requires models with `supports_tools = true`.                        |

Additional custom fields can be introduced in future releases; validation will ignore unknown keys with a warning.

---

## 6. Built-in Profiles (Phase 9 baseline)

| Profile   | Temperature | Max Tokens | Reasoning Depth | Speed vs Accuracy | Cost Sensitivity | Multimodal | JSON Mode | Tool Use | Primary Use Case          |
|-----------|-------------|------------|-----------------|-------------------|------------------|------------|-----------|----------|---------------------------|
| `fast`    | 0.2         | 1024       | minimal         | speed             | medium           | false      | false     | false    | Real-time, quick replies  |
| `balanced`| 0.7         | 2048       | standard        | balanced          | medium           | false      | false     | true     | General-purpose default   |
| `reasoning`| 0.2        | 4000       | deep            | accuracy          | high             | false      | false     | true     | Complex reasoning tasks   |
| `vision`  | 0.3         | 2048       | standard        | balanced          | medium           | true       | false     | false    | Multimodal (images)       |
| `json`    | 0.1         | 2000       | standard        | accuracy          | medium           | false      | true      | false    | Structured JSON responses |
| `cheap`   | 0.4         | 1024       | minimal         | speed             | high             | false      | false     | false    | Cost-sensitive workloads  |

All built-ins live at `stratifyai/profiles/profiles.yaml`. They can be overridden by placing a profile with the same name in the user directory.

---

## 7. Profile Inheritance

Profiles can extend existing profiles via the `extends` field.  
Inheritance rules:
1. Load parent profile first (recursively resolving its parent).
2. Merge child parameters on top of parent.
3. Child overrides replace parent values.
4. Cycles are rejected with a validation error.

Example:

```yaml
profiles:
  - name: base-balanced
    parameters:
      temperature: 0.6
      max_tokens: 2048
      speed_vs_accuracy: balanced

  - name: enterprise-audit
    extends: base-balanced
    parameters:
      json_mode: true
      tool_use: false
    tags: [compliance]
```

---

## 8. CLI Usage

### List profiles
```bash
stratifyai profiles --verbose
```

### Use profile with overrides
```bash
stratifyai chat \
  --profile reasoning \
  --profile-param max_tokens=2500 \
  --message "Summarize EU AI Act."
```

### Filter by tag
```bash
stratifyai profiles --tag cost
```

Exit codes:
- `0` on success.
- `1` if profile not found or validation fails.

---

## 9. REST API Endpoints

1. `GET /api/profiles`  
   - Query params: `tag`, `source`.  
   - Returns list of profile metadata (no secrets).

2. `GET /api/profiles/{name}`  
   - Returns full configuration, including inherited values and capability hints.

3. `POST /api/profiles/{name}/validate`  
   - Body: `{ "provider": "...", "model": "...", "overrides": {...} }`  
   - Validates compatibility; returns `{"valid": true}` or detailed error.

4. `POST /api/profiles/{name}/resolve`  
   - Body: same as validate.  
  遂  - Returns final parameter map that would be applied.

All endpoints require authentication when `STRATIFYAI_API_KEY` is set.

---

## 10. Python Usage Patterns

```python
from stratifyai.chat import anthropic

builder = (
    anthropic
    .with_model("claude-3-5-sonnet")
    .with_profile("json", max_tokens=1500)
)

response = builder.chat_sync("Generate release notes in JSON.")
print(response.content)
```

- `with_profile` accepts overrides via keyword arguments.
- Explicit builder methods (e.g., `.with_temperature(0.9)`) take precedence.
- Advanced: Access the registry directly.

```python
from stratifyai.profiles import registry

profile = registry.get("cheap")
effective = registry.render("cheap", overrides={"temperature": 0.1})
```

---

## 11. User-defined Profiles

### Location
- macOS/Linux: `~/.stratifyai/profiles/`
- Windows: `%USERPROFILE%\.stratifyai\profiles\`

### Reload behavior
- Profiles are loaded lazily; restart the process or clear the registry cache (planned API: `registry.reload()`).

### Best practices
- Start from built-in examples.
- Use descriptive `tags` for filtering.
- Include `notes` with author/contact info in team environments.

---

## 12. Validation & Error Messages

Common errors:
- **ProfileNotFound**: Name not registered.
- **ValidationError**: Invalid parameter type or value.
- **CapabilityError**: Model lacks required capability (vision, tools, JSON).
- **InheritanceError**: Parent profile missing or cycle detected.

Example message:
```
Profile 'vision' cannot be applied to provider 'gpt-4.1-mini':
model does not support multimodal inputs (multimodal=true).
```

---

## 13. Router Integration

Profiles communicate intent to the router:
- `speed_vs_accuracy = speed` → prefer low-latency models.
- `cost_sensitivity = high` → penalize expensive candidates.
- `speed_vs_accuracy = accuracy` or `cost_sensitivity = low` → bias toward quality models.

These hints are advisory and combine with explicit CLI/API routing strategy flags.

---

## 14. Configuration Precedence

1. **Explicit arguments** (ChatBuilder methods, CLI flags, API payload).
2. **Profile parameters** (including inherited values).
3. **Default settings** (builder defaults, global config).

Documented precedence ensures deterministic behavior and prevents accidental overrides.

---

## 15. Security & Compliance Notes

- Profiles are plain text YAML; avoid storing secrets in profile files.
- User profile directory inherits OS-level permissions.
- Validation ensures models cannot be forced into unsupported modes (e.g., JSON mode on non-compliant models).

---

## 16. Future Enhancements

- Profile versioning and audit history.
- Team-shared profile repositories.
- UI-based profile editor in the StratifyAI dashboard.
- Hooks for dynamic profile selection based on request metadata.

---

## 17. Getting Help

- Consult `docs/PROFILE-SYSTEM-PLAN.md` for engineering details.
- Review `developer-journal.md` for implementation milestones.
- Open issues or feature requests via GitHub using the `profiles` label.