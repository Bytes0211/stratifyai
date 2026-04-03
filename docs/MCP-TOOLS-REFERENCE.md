# MCP Tools Reference

Complete reference for all StratifyAI MCP tools, resources, and prompts.

---

## Tools

### `chat_completion`

Send a chat completion request to a specific provider and model.

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `provider` | string | Yes | | Provider name (e.g. "openai", "anthropic") |
| `model` | string | Yes | | Model ID (e.g. "gpt-4.1-mini") |
| `messages` | list[{role, content}] | Yes | | Conversation messages |
| `temperature` | float | No | 0.7 | Sampling temperature |
| `max_tokens` | int | No | None | Maximum response tokens |

**Output:**

```json
{
  "content": "Hello! How can I help you today?",
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "prompt_tokens": 12,
  "completion_tokens": 9,
  "total_tokens": 21,
  "cost_usd": 0.000063,
  "latency_ms": 450.2,
  "mcp_schema_version": 1
}
```

---

### `chat_with_routing`

Route a chat request to the best provider/model using a strategy.

**Inputs:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `messages` | list[{role, content}] | Yes | | Conversation messages |
| `strategy` | string | No | "hybrid" | Routing strategy: cost, quality, latency, hybrid |
| `capabilities` | list[string] | No | None | Required capabilities (e.g. ["vision", "tools"]) |
| `preferred_providers` | list[string] | No | None | Preferred providers to prioritize |
| `excluded_providers` | list[string] | No | None | Providers to exclude |
| `max_cost_usd` | float | No | None | Maximum cost per 1k tokens |
| `max_latency_ms` | float | No | None | Maximum acceptable latency |

**Output:**

```json
{
  "selected_provider": "deepseek",
  "selected_model": "deepseek-chat",
  "routing_strategy": "cost",
  "content": "Response text...",
  "prompt_tokens": 15,
  "completion_tokens": 42,
  "cost_usd": 0.000008,
  "latency_ms": 890.5,
  "mcp_schema_version": 1
}
```

---

### `list_providers`

List all available providers with their model count and configuration status.

**Inputs:** None

**Output:**

```json
[
  {"provider": "openai", "model_count": 12, "configured": true},
  {"provider": "anthropic", "model_count": 6, "configured": true},
  {"provider": "google", "model_count": 8, "configured": false}
]
```

---

### `list_models`

List all models for a given provider with key metadata.

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider` | string | Yes | Provider name |

**Output:**

```json
[
  {
    "model_id": "gpt-4.1-mini",
    "context_window": 1047576,
    "cost_input_per_1m": 0.40,
    "cost_output_per_1m": 1.60,
    "capabilities": ["vision", "tools", "streaming"]
  }
]
```

---

### `get_model_info`

Get full metadata for a specific model.

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider` | string | Yes | Provider name |
| `model` | string | Yes | Model ID |

**Output:**

```json
{
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "metadata": {
    "context": 1047576,
    "cost_input": 0.40,
    "cost_output": 1.60,
    "supports_vision": true,
    "supports_tools": true,
    "supports_streaming": true
  },
  "mcp_schema_version": 1
}
```

---

### `get_cost_summary`

Get cost summary for the current MCP session.

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider` | string | No | Filter by provider |
| `model` | string | No | Filter by model |

**Output:**

```json
{
  "total_cost_usd": 0.0052,
  "total_calls": 8,
  "total_tokens": 1540,
  "by_provider": {"openai": 0.004, "anthropic": 0.0012},
  "by_model": {"gpt-4.1-mini": 0.004},
  "mcp_schema_version": 1
}
```

---

### `validate_provider`

Validate that a provider is configured and accessible.

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider` | string | Yes | Provider name |

**Output:**

```json
{
  "provider": "openai",
  "configured": true,
  "models_available": ["gpt-4.1", "gpt-4.1-mini", "gpt-4o", "o3-mini"],
  "validation_errors": [],
  "mcp_schema_version": 1
}
```

---

### `estimate_cost`

Estimate the token count and cost for a message with a given provider/model.

**Inputs:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider` | string | Yes | Provider name |
| `model` | string | Yes | Model ID |
| `message_text` | string | Yes | Text to estimate |

**Output:**

```json
{
  "estimated_input_tokens": 256,
  "estimated_cost_usd": 0.000102,
  "provider": "openai",
  "model": "gpt-4.1-mini",
  "mcp_schema_version": 1
}
```

---

## Resources

Resources provide read-only context data to MCP clients without requiring a tool call.

| URI | Description |
|-----|-------------|
| `stratifyai://catalog` | Full model catalog (all providers, all models) as JSON |
| `stratifyai://catalog/{provider}` | Models for a single provider (e.g. `stratifyai://catalog/openai`) |
| `stratifyai://providers` | Provider list with model count and configured status |
| `stratifyai://costs` | Current session cost summary |
| `stratifyai://router/strategies` | Available routing strategies with descriptions |

---

## Prompts

### Named Prompts

| Prompt | Arguments | Description |
|--------|-----------|-------------|
| `compare_models` | `models` (comma-separated "provider/model" pairs) | Compare models across capabilities, pricing, speed |
| `recommend_model` | `task_description`, `budget?`, `priority?` | Recommend best model for a task |
| `analyze_costs` | `time_period?` | Analyze session costs with optimization suggestions |

### Dynamic Template Prompts

All built-in prompt templates from `stratifyai/prompts/templates/` are also exposed as MCP prompts with the prefix `template_`. For example:

- `template_code_review` — Code review prompt
- `template_summarize` — Text summarization prompt
- `template_chatbot` — General chatbot prompt

User-defined templates in `~/.stratifyai/prompts/` are also exposed automatically.

---

## Error Responses

All tools return structured errors on failure:

```json
{
  "error_code": "invalid_provider",
  "error_type": "InvalidProviderError",
  "message": "Provider 'foo' is not supported",
  "provider": "foo"
}
```

**Error Codes:**

| Code | Description |
|------|-------------|
| `auth_failed` | API key missing or invalid |
| `invalid_provider` | Unknown provider name |
| `invalid_model` | Unknown model for the given provider |
| `budget_exceeded` | Cost budget limit reached |
| `provider_error` | Provider API returned an error |
| `rate_limited` | Provider rate limit hit |
| `validation_error` | Invalid input parameters |
| `internal_error` | Unexpected server error |
