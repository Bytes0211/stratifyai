# Adding New Models to StratifyAI

**Purpose**: This guide provides step-by-step instructions for adding new models to StratifyAI, including all required metadata for cost tracking, capability detection, and router intelligence.

**Last Updated**: February 3, 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Reference: Metadata Fields](#quick-reference-metadata-fields)
3. [Step-by-Step: Adding a New Model](#step-by-step-adding-a-new-model)
4. [Finding Pricing Information](#finding-pricing-information)
5. [Testing New Models](#testing-new-models)
6. [Provider-Specific Notes](#provider-specific-notes)
7. [Common Pitfalls](#common-pitfalls)
8. [Examples](#examples)

---

## Overview

### Why Manual Model Addition?

StratifyAI maintains a **hardcoded model catalog** in `llm_abstraction/config.py` because:
- **Cost tracking** requires pricing data (not available via APIs)
- **Capability metadata** enables intelligent routing (vision, tools, reasoning, caching)
- **Production stability** prevents surprise bills from auto-discovered models
- **Budget enforcement** requires known costs per token

### What Happens When You Add a Model

1. **Cost tracking**: Every API call calculates exact costs based on your metadata
2. **Router intelligence**: Model selector uses capabilities to choose optimal model
3. **CLI display**: Model appears in `stratifyai models --provider <name>`
4. **Interactive mode**: Model available in provider selection menus
5. **Validation**: Client validates model exists before making API calls

---

## Quick Reference: Metadata Fields

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `context` | int | Maximum context window (tokens) | `200000` |
| `cost_input` | float | Input cost per 1M tokens (USD) | `3.0` |
| `cost_output` | float | Output cost per 1M tokens (USD) | `15.0` |
| `supports_vision` | bool | Image input support | `True` |
| `supports_tools` | bool | Function calling support | `True` |

### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `cost_cache_write` | float | Prompt cache write cost per 1M tokens | `3.75` |
| `cost_cache_read` | float | Prompt cache read cost per 1M tokens | `0.30` |
| `supports_caching` | bool | Prompt caching support | `True` |
| `reasoning_model` | bool | Reasoning model (o1, o3 series) | `True` |
| `fixed_temperature` | float | Fixed temperature (for reasoning models) | `1.0` |
| `api_max_input` | int | API-enforced input limit (if different from context) | `200000` |
| `free` | bool | Free model (for OpenRouter) | `True` |

### Field Details

#### `context` (Required)
- **Purpose**: Maximum context window size in tokens
- **How to find**: Check provider's model documentation
- **Notes**: 
  - For models with different input/output limits, use the **input** limit
  - If API enforces lower limit than advertised, add `api_max_input` field

#### `cost_input` / `cost_output` (Required)
- **Purpose**: Pricing per 1 million tokens
- **Units**: USD per 1M tokens
- **How to find**: Provider's pricing page (see [Finding Pricing Information](#finding-pricing-information))
- **Examples**:
  - $3.00 per 1M input tokens → `"cost_input": 3.0`
  - $0.50 per 1M output tokens → `"cost_output": 0.50`
  - Free models → `"cost_input": 0.0, "cost_output": 0.0`

#### `cost_cache_write` / `cost_cache_read` (Optional)
- **Purpose**: Prompt caching costs (Anthropic, OpenAI only)
- **When to include**: If model supports prompt caching
- **Common patterns**:
  - Cache write: **125% of input cost** (e.g., $3.00 input → $3.75 cache write)
  - Cache read: **10% of input cost** (e.g., $3.00 input → $0.30 cache read)
- **Must also set**: `"supports_caching": True`

#### `supports_vision` (Required)
- **Purpose**: Whether model accepts image inputs
- **Values**: `True` or `False`
- **How to determine**: Check provider's feature matrix
- **Examples**:
  - GPT-4o, Claude Sonnet, Gemini → `True`
  - GPT-3.5-turbo, o1 series → `False`

#### `supports_tools` (Required)
- **Purpose**: Whether model supports function calling
- **Values**: `True` or `False`
- **How to determine**: Check provider's API documentation
- **Notes**: Most modern models support tools; older/smaller models may not

#### `supports_caching` (Optional)
- **Purpose**: Whether model supports prompt caching
- **Values**: `True` or `False`
- **Providers with caching**:
  - **OpenAI**: GPT-4o, GPT-4o-mini (set to `True`)
  - **Anthropic**: All Claude 3+ models (set to `True`)
  - **AWS Bedrock**: None yet (set to `False`)
  - **Others**: Generally `False` (omit field)

#### `reasoning_model` (Optional)
- **Purpose**: Identifies reasoning models (o1, o3, DeepSeek R1)
- **Values**: `True` or omit field (defaults to `False`)
- **Behavior changes**:
  - Temperature fixed at 1.0 (cannot be changed)
  - No streaming support in some implementations
  - Special handling in OpenAI provider (lines 104-117 in openai.py)
- **Examples**: `o1`, `o1-mini`, `o3-mini`, `deepseek-reasoner`

#### `fixed_temperature` (Optional)
- **Purpose**: Force specific temperature (for reasoning models)
- **Values**: `1.0` (only used with reasoning models)
- **When to include**: Only for reasoning models that require temperature=1.0

#### `api_max_input` (Optional)
- **Purpose**: API-enforced input limit (when different from context window)
- **Example**: Claude Opus 4.5 has 1M context but API limits to 200k input
- **Usage**:
  ```python
  "claude-opus-4-5-20251101": {
      "context": 1000000,
      "api_max_input": 200000,  # API enforces 200k input limit
      ...
  }
  ```

#### `free` (Optional)
- **Purpose**: Mark free models (OpenRouter only)
- **Values**: `True` or omit field
- **When to include**: OpenRouter free-tier models
- **Usage**: Helps users identify cost-free options

---

## Step-by-Step: Adding a New Model

### Step 1: Determine Provider

Identify which provider the model belongs to:
- `openai` - OpenAI models (GPT series, o1 series)
- `anthropic` - Anthropic models (Claude series)
- `google` - Google models (Gemini series)
- `deepseek` - DeepSeek models
- `groq` - Groq models
- `grok` - Grok (X.AI) models
- `openrouter` - OpenRouter aggregated models
- `ollama` - Ollama local models
- `bedrock` - AWS Bedrock models

### Step 2: Gather Required Information

Collect the following information from provider's documentation:

1. **Exact model ID** (e.g., `gpt-4o`, `claude-sonnet-4-5-20250929`)
2. **Context window size** (tokens)
3. **Input pricing** (per 1M tokens)
4. **Output pricing** (per 1M tokens)
5. **Vision support** (yes/no)
6. **Function calling support** (yes/no)

### Step 3: Gather Optional Information (if applicable)

7. **Cache write pricing** (if model supports caching)
8. **Cache read pricing** (if model supports caching)
9. **Reasoning model** (if o1/o3 series or DeepSeek reasoner)
10. **API input limits** (if different from context window)

### Step 4: Add to Provider's Model Dictionary

Open `llm_abstraction/config.py` and locate the appropriate provider dictionary:

```python
# For OpenAI models → OPENAI_MODELS
# For Anthropic models → ANTHROPIC_MODELS
# For Google models → GOOGLE_MODELS
# For DeepSeek models → DEEPSEEK_MODELS
# For Groq models → GROQ_MODELS
# For Grok models → GROK_MODELS
# For OpenRouter models → OPENROUTER_MODELS
# For Ollama models → OLLAMA_MODELS
# For Bedrock models → BEDROCK_MODELS
```

Add your model entry:

```python
"model-id-here": {
    "context": 128000,
    "cost_input": 3.0,
    "cost_output": 15.0,
    "supports_vision": True,
    "supports_tools": True,
    "supports_caching": True,  # Optional
    "cost_cache_write": 3.75,  # Optional
    "cost_cache_read": 0.30,   # Optional
    "reasoning_model": False,  # Optional
    "fixed_temperature": 1.0,  # Optional (reasoning models only)
},
```

### Step 5: Update Provider Constraints (if needed)

If adding a **new provider** (not just a new model), update `PROVIDER_CONSTRAINTS`:

```python
PROVIDER_CONSTRAINTS: Dict[str, Dict[str, Any]] = {
    # ... existing providers ...
    "new_provider": {
        "min_temperature": 0.0,
        "max_temperature": 1.0,  # Check provider docs
    },
}
```

### Step 6: Verify MODEL_CATALOG Registration

Ensure the provider's model dictionary is registered in `MODEL_CATALOG` (line 1017+):

```python
MODEL_CATALOG: Dict[str, Dict[str, Dict[str, Any]]] = {
    "openai": OPENAI_MODELS,
    "anthropic": ANTHROPIC_MODELS,
    # ... ensure your provider is listed ...
}
```

### Step 7: Test the Model

See [Testing New Models](#testing-new-models) section below.

---

## Finding Pricing Information

### Provider Pricing Pages

| Provider | Pricing URL |
|----------|-------------|
| **OpenAI** | https://openai.com/api/pricing/ |
| **Anthropic** | https://www.anthropic.com/pricing |
| **Google (Gemini)** | https://ai.google.dev/pricing |
| **DeepSeek** | https://platform.deepseek.com/api-docs/pricing/ |
| **Groq** | https://groq.com/pricing/ |
| **Grok (X.AI)** | https://x.ai/api/pricing |
| **OpenRouter** | https://openrouter.ai/models (per-model pricing) |
| **AWS Bedrock** | https://aws.amazon.com/bedrock/pricing/ |
| **Ollama** | Free (local models) |

### Pricing Format Conversion

Providers display pricing in different formats. Convert to **USD per 1M tokens**:

| Provider Format | Example | Conversion | config.py Value |
|-----------------|---------|------------|-----------------|
| Per 1M tokens | $3.00 / 1M tokens | No conversion | `3.0` |
| Per 1K tokens | $0.003 / 1K tokens | Multiply by 1000 | `3.0` |
| Per token | $0.000003 / token | Multiply by 1,000,000 | `3.0` |

### Cache Pricing Patterns

Most providers follow these patterns:

| Cache Type | Typical Cost | Example (Input = $3.00) |
|------------|--------------|-------------------------|
| Cache Write | Input × 1.25 | $3.75 per 1M tokens |
| Cache Read | Input × 0.10 | $0.30 per 1M tokens |

**Formula**:
```python
cost_cache_write = cost_input * 1.25
cost_cache_read = cost_input * 0.10
```

---

## Testing New Models

### Test 1: Verify Model Appears in CLI

```bash
python -m cli.stratifyai_cli models --provider <provider_name>
```

Expected output:
```
Available models for openai:
  1. gpt-4o (128000 tokens)
  2. your-new-model (200000 tokens)  # ← Should appear here
  ...
```

### Test 2: Basic Chat Completion

```bash
python -m cli.stratifyai_cli chat \
  --provider <provider> \
  --model <model-id> \
  --prompt "Hello, test message"
```

Expected: Response from model with cost displayed.

### Test 3: Interactive Mode

```bash
python -m cli.stratifyai_cli interactive --provider <provider>
```

Then:
1. Select your new model from the menu
2. Send a test message
3. Verify cost tracking displays correctly

### Test 4: Cost Calculation

```python
# Create test script: test_new_model.py
from stratifyai import LLMClient
from stratifyai.models import ChatRequest, Message

client = LLMClient()

request = ChatRequest(
    model="your-new-model",
    messages=[Message(role="user", content="Say 'test' once")]
)

response = client.chat_completion("provider_name", request)

print(f"Model: {response.model}")
print(f"Input tokens: {response.usage.prompt_tokens}")
print(f"Output tokens: {response.usage.completion_tokens}")
print(f"Total cost: ${response.usage.total_cost:.6f}")
```

Run:
```bash
python test_new_model.py
```

Verify:
- Cost is non-zero (unless free model)
- Cost matches expected value based on token counts

### Test 5: Provider Unit Tests

If adding to existing provider, verify unit tests pass:

```bash
pytest tests/test_<provider>_provider.py -v
```

If tests fail, you may need to:
1. Add model to test fixtures
2. Update test assertions for new model count

---

## Provider-Specific Notes

### OpenAI

**Model ID Format**: `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini`

**Reasoning Models**: Models starting with `o1`, `o3`, `gpt-5` require:
```python
"reasoning_model": True,
"fixed_temperature": 1.0,
```

**Caching**: GPT-4o and GPT-4o-mini support caching:
```python
"supports_caching": True,
"cost_cache_write": 1.25,  # Example
"cost_cache_read": 1.25,
```

**Temperature Range**: 0.0 to 2.0 (most providers limit to 1.0)

---

### Anthropic

**Model ID Format**: `claude-sonnet-4-5-20250929`, `claude-opus-4-20250514`

**Aliases**: Anthropic provides aliases (e.g., `claude-sonnet-4-5` → latest Sonnet 4.5)
- Add both versioned model AND alias to catalog
- Use same metadata for both entries

**Caching**: All Claude 3+ models support caching:
```python
"supports_caching": True,
"cost_cache_write": 3.75,  # Input × 1.25
"cost_cache_read": 0.30,   # Input × 0.10
```

**Vision**: All Claude 3+ models support vision (set `"supports_vision": True`)

**Temperature Range**: 0.0 to 1.0

**API Limits**: Claude Opus 4.5 has special case:
```python
"claude-opus-4-5-20251101": {
    "context": 1000000,        # Advertised context
    "api_max_input": 200000,   # API enforces 200k input
    ...
}
```

---

### Google (Gemini)

**Model ID Format**: `gemini-1.5-pro`, `gemini-1.5-flash`, `gemini-2.0-flash-exp`

**Flash Models**: Typically faster/cheaper:
```python
"gemini-1.5-flash": {
    "context": 1000000,
    "cost_input": 0.075,   # Much cheaper
    "cost_output": 0.30,
    ...
}
```

**Experimental Models**: Models ending in `-exp` may have unstable pricing

**Temperature Range**: 0.0 to 2.0

---

### DeepSeek

**Model ID Format**: `deepseek-chat`, `deepseek-reasoner`

**Reasoner Model**: DeepSeek's reasoning model:
```python
"deepseek-reasoner": {
    "context": 64000,
    "cost_input": 0.55,
    "cost_output": 2.19,
    "reasoning_model": True,  # Important!
    "fixed_temperature": 1.0,
    "supports_vision": False,
    "supports_tools": False,
}
```

**Temperature Range**: 0.0 to 2.0

---

### Groq

**Model ID Format**: `llama-3.3-70b-versatile`, `mixtral-8x7b-32768`

**Context in Model ID**: Some models include context window in ID (ignore it, use metadata)

**Free Tier**: Groq models are typically free or very cheap

**Temperature Range**: 0.0 to 2.0

---

### Grok (X.AI)

**Model ID Format**: `grok-beta`, `grok-vision-beta`

**Beta Models**: Most Grok models are in beta

**Temperature Range**: 0.0 to 2.0

---

### OpenRouter

**Model ID Format**: `<provider>/<model>` (e.g., `anthropic/claude-3-5-sonnet`)

**Free Models**: OpenRouter offers free-tier models:
```python
"openai/gpt-3.5-turbo:free": {
    "context": 16385,
    "cost_input": 0.0,
    "cost_output": 0.0,
    "supports_vision": False,
    "supports_tools": True,
    "free": True,  # Mark as free
}
```

**Pricing**: Check OpenRouter's model page for per-model pricing

**Temperature Range**: 0.0 to 2.0

---

### Ollama

**Model ID Format**: `llama3.2`, `mistral`, `codellama`

**Local Models**: All Ollama models are free (local execution):
```python
"llama3.2": {
    "context": 128000,
    "cost_input": 0.0,
    "cost_output": 0.0,
    "supports_vision": False,
    "supports_tools": False,
}
```

**Dynamic Catalog**: Ollama models depend on what's installed locally

**Temperature Range**: 0.0 to 2.0

---

### AWS Bedrock

**Model ID Format**: `<provider>.<model>-<version>` (e.g., `anthropic.claude-3-5-sonnet-20241022-v2:0`)

**Caching**: Bedrock does NOT support prompt caching (yet):
```python
"supports_caching": False,  # Important!
```

**Pricing**: Check AWS Bedrock pricing by region (use us-east-1 as baseline)

**Temperature Range**: Varies by model family
- Anthropic Claude: 0.0 to 1.0
- Meta Llama: 0.0 to 1.0
- Others: Check docs

**Model Families**:
- Anthropic Claude: Support vision, tools
- Meta Llama: No vision, no tools
- Mistral: No vision, support tools
- Amazon Titan: No vision, no tools
- Cohere: No vision, support tools

---

## Common Pitfalls

### 1. Wrong Pricing Units

❌ **Wrong**:
```python
# Pricing is $0.003 per 1K tokens
"cost_input": 0.003,  # This is WRONG!
```

✅ **Correct**:
```python
# Pricing is $0.003 per 1K tokens → $3.00 per 1M tokens
"cost_input": 3.0,  # Multiply by 1000
```

### 2. Missing Required Fields

❌ **Wrong**:
```python
"new-model": {
    "context": 128000,
    # Missing cost_input, cost_output, supports_vision, supports_tools
}
```

✅ **Correct**:
```python
"new-model": {
    "context": 128000,
    "cost_input": 3.0,
    "cost_output": 15.0,
    "supports_vision": True,
    "supports_tools": True,
}
```

### 3. Incorrect Cache Pricing

❌ **Wrong**:
```python
"cost_cache_write": 3.0,  # Same as input cost
"cost_cache_read": 3.0,   # Same as input cost
```

✅ **Correct**:
```python
"cost_cache_write": 3.75,  # Input × 1.25
"cost_cache_read": 0.30,   # Input × 0.10
```

### 4. Forgetting `supports_caching` with Cache Costs

❌ **Wrong**:
```python
"cost_cache_write": 3.75,
"cost_cache_read": 0.30,
# Missing supports_caching: True
```

✅ **Correct**:
```python
"cost_cache_write": 3.75,
"cost_cache_read": 0.30,
"supports_caching": True,  # Required!
```

### 5. Wrong Boolean Types

❌ **Wrong**:
```python
"supports_vision": "True",  # String, not bool
"supports_tools": 1,        # Integer, not bool
```

✅ **Correct**:
```python
"supports_vision": True,  # Boolean
"supports_tools": False,  # Boolean
```

### 6. Inconsistent Model IDs

❌ **Wrong**:
```python
# In config.py
"gpt-4o-mini": { ... }

# In test
response = client.chat_completion("openai", "gpt-4o-mini-2024")  # ID mismatch
```

✅ **Correct**: Use exact model ID from config.py

### 7. Missing Provider Registration

❌ **Wrong**: Add model to `OPENAI_MODELS` but forget to register provider in `MODEL_CATALOG`

✅ **Correct**: Always verify provider is in `MODEL_CATALOG` (line 1017)

---

## Examples

### Example 1: Standard Model (GPT-4o)

```python
"gpt-4o": {
    "context": 128000,
    "cost_input": 2.5,
    "cost_output": 10.0,
    "cost_cache_write": 1.25,
    "cost_cache_read": 1.25,
    "supports_vision": True,
    "supports_tools": True,
    "supports_caching": True,
},
```

**Notes**:
- Supports vision, tools, caching
- Cache costs provided
- Standard context window

### Example 2: Reasoning Model (o1)

```python
"o1": {
    "context": 200000,
    "cost_input": 15.0,
    "cost_output": 60.0,
    "supports_vision": False,
    "supports_tools": False,
    "reasoning_model": True,
    "fixed_temperature": 1.0,
},
```

**Notes**:
- No vision, no tools (reasoning models are restricted)
- `reasoning_model: True` enables special handling
- `fixed_temperature: 1.0` required

### Example 3: Claude with Caching (Anthropic)

```python
"claude-sonnet-4-5-20250929": {
    "context": 200000,
    "cost_input": 3.0,
    "cost_output": 15.0,
    "cost_cache_write": 3.75,  # 3.0 × 1.25
    "cost_cache_read": 0.30,   # 3.0 × 0.10
    "supports_vision": True,
    "supports_tools": True,
    "supports_caching": True,
},
```

**Notes**:
- Cache write = input × 1.25
- Cache read = input × 0.10
- All Claude 3+ support caching

### Example 4: Claude with API Limit (Opus 4.5)

```python
"claude-opus-4-5-20251101": {
    "context": 1000000,
    "api_max_input": 200000,  # API enforces 200k despite 1M context
    "cost_input": 5.0,
    "cost_output": 25.0,
    "cost_cache_write": 6.25,
    "cost_cache_read": 0.50,
    "supports_vision": True,
    "supports_tools": True,
    "supports_caching": True,
},
```

**Notes**:
- `api_max_input` handles API-enforced limit
- Different from advertised context window

### Example 5: Free Model (OpenRouter)

```python
"openai/gpt-3.5-turbo:free": {
    "context": 16385,
    "cost_input": 0.0,
    "cost_output": 0.0,
    "supports_vision": False,
    "supports_tools": True,
    "free": True,
},
```

**Notes**:
- Zero costs for free models
- `free: True` marks as free-tier

### Example 6: Bedrock Model (No Caching)

```python
"anthropic.claude-3-5-sonnet-20241022-v2:0": {
    "context": 200000,
    "cost_input": 3.0,
    "cost_output": 15.0,
    "supports_vision": True,
    "supports_tools": True,
    "supports_caching": False,  # Bedrock doesn't support caching
},
```

**Notes**:
- Bedrock uses different model ID format
- Caching not supported (yet)

### Example 7: Local Model (Ollama)

```python
"llama3.2": {
    "context": 128000,
    "cost_input": 0.0,
    "cost_output": 0.0,
    "supports_vision": False,
    "supports_tools": False,
},
```

**Notes**:
- Zero costs (local execution)
- Limited capabilities

### Example 8: DeepSeek Reasoner

```python
"deepseek-reasoner": {
    "context": 64000,
    "cost_input": 0.55,
    "cost_output": 2.19,
    "supports_vision": False,
    "supports_tools": False,
    "reasoning_model": True,
    "fixed_temperature": 1.0,
},
```

**Notes**:
- Reasoning model flag enables special handling
- Lower context window than chat models
- No vision, no tools

---

## Checklist: Adding a New Model

Use this checklist when adding a new model:

- [ ] Gathered exact model ID from provider docs
- [ ] Found context window size (tokens)
- [ ] Found input pricing (converted to USD per 1M tokens)
- [ ] Found output pricing (converted to USD per 1M tokens)
- [ ] Determined vision support (yes/no)
- [ ] Determined function calling support (yes/no)
- [ ] Checked if model supports caching (if yes, get cache pricing)
- [ ] Checked if model is reasoning model (o1/o3/DeepSeek reasoner)
- [ ] Added model entry to appropriate provider dictionary in `config.py`
- [ ] Verified provider is registered in `MODEL_CATALOG`
- [ ] Tested model appears in CLI: `python -m cli.stratifyai_cli models --provider <name>`
- [ ] Tested basic chat completion works
- [ ] Tested cost tracking displays correctly
- [ ] Updated documentation if adding new provider

---

## Maintenance Schedule

**Recommended frequency**: Monthly review of provider release notes

### Monthly Tasks

1. Check provider websites for new model releases:
   - OpenAI: https://openai.com/blog
   - Anthropic: https://www.anthropic.com/news
   - Google: https://ai.google.dev/gemini-api/docs/models
   - Others: Check respective provider blogs

2. Update pricing if changed (rare but happens)

3. Deprecate old models (mark with comment, don't remove)

4. Test cost tracking accuracy with sample requests

---

## Support

**Questions?** 
- Check existing model definitions in `llm_abstraction/config.py` for patterns
- Review provider-specific implementations in `llm_abstraction/providers/<provider>.py`
- Test thoroughly before deploying to production

**Found a bug?**
- Verify pricing is correct on provider's website
- Check unit tests in `tests/test_<provider>_provider.py`
- Review cost calculation logic in `llm_abstraction/providers/base.py`

---

## Appendix: Complete Template

Copy this template when adding a new model:

```python
"model-id-here": {
    # Required fields
    "context": 128000,              # Maximum context window (tokens)
    "cost_input": 0.0,              # Input cost per 1M tokens (USD)
    "cost_output": 0.0,             # Output cost per 1M tokens (USD)
    "supports_vision": False,       # Image input support
    "supports_tools": False,        # Function calling support
    
    # Optional: Caching (if supported)
    # "supports_caching": True,
    # "cost_cache_write": 0.0,      # Cache write cost per 1M tokens
    # "cost_cache_read": 0.0,       # Cache read cost per 1M tokens
    
    # Optional: Reasoning model
    # "reasoning_model": True,
    # "fixed_temperature": 1.0,
    
    # Optional: API limits
    # "api_max_input": 200000,      # If API enforces lower input limit
    
    # Optional: Free model (OpenRouter only)
    # "free": True,
},
```

---

**End of Guide**
