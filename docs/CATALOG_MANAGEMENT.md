# Community-Friendly Model Catalog Management

**Version:** 1.0.0  
**Last Updated:** February 6, 2026  
**Status:** Production Ready

## Overview

StratifyAI's model catalog is **community-editable** and stored in `catalog/models.json`. This enables the community to keep model metadata current without waiting for maintainer updates. All catalog changes are automatically validated via GitHub Actions CI/CD.

## Table of Contents

- [Why Externalize the Catalog?](#why-externalize-the-catalog)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [Catalog Structure](#catalog-structure)
- [Model ID Conventions](#model-id-conventions)
- [Deprecation Management](#deprecation-management)
- [Validation & CI/CD](#validation--cicd)
- [Auto-Sync System](#auto-sync-system)
- [FAQ](#faq)

## Why Externalize the Catalog?

### The Problem

Previously, model metadata was hardcoded in Python:
- ❌ Difficult for community to contribute
- ❌ Required code changes for pricing updates
- ❌ No automated deprecation detection
- ❌ Hypothetical/future models mixed with real ones
- ❌ Provider updates caused 404 errors (e.g., Anthropic bug)

### The Solution

JSON catalog with community contribution:
- ✅ Anyone can submit PRs to update models
- ✅ CI automatically validates all changes
- ✅ Deprecation tracking built-in
- ✅ Only dated model IDs allowed
- ✅ Provider validator detects deprecated models

## Architecture

### Data Flow

```
catalog/models.json (source of truth)
    ↓
catalog_manager.py (loads & caches)
    ↓
config.py (ANTHROPIC_MODELS, etc.)
    ↓
providers/*.py (BaseProvider implementations)
    ↓
API/CLI (user-facing interfaces)
```

### Components

1. **`catalog/models.json`** - Model metadata (pricing, capabilities)
2. **`catalog/schema.json`** - JSON schema for validation
3. **`catalog/README.md`** - Contribution guidelines
4. **`stratifyai/catalog_manager.py`** - Loads catalog with caching
5. **`scripts/validate_catalog.py`** - Validation tool
6. **`.github/workflows/validate-catalog.yml`** - CI automation

## Contributing

### Quick Start

1. **Fork** the repository
2. **Edit** `catalog/models.json`
3. **Validate** locally:
   ```bash
   python scripts/validate_catalog.py
   ```
4. **Commit** with descriptive message
5. **Create PR** - CI will auto-validate

### When to Contribute

Submit a PR when:
- ✅ New model released by provider
- ✅ Model pricing changed
- ✅ Model deprecated/retired
- ✅ Capability updated (vision, tools, caching)
- ✅ Incorrect metadata needs correction

### Contribution Examples

#### Adding a New Model

```json
{
  "providers": {
    "anthropic": {
      "claude-opus-4-6-20260205": {
        "display_name": "Claude Opus 4.6",
        "description": "Latest flagship, agent teams",
        "category": "Claude 4.6 (Latest)",
        "context": 200000,
        "cost_input": 5.0,
        "cost_output": 25.0,
        "cost_cache_write": 6.25,
        "cost_cache_read": 0.50,
        "supports_vision": true,
        "supports_tools": true,
        "supports_caching": true
      }
    }
  }
}
```

#### Marking Model as Deprecated

```json
{
  "claude-3-5-sonnet-20241022": {
    "context": 200000,
    "cost_input": 3.0,
    "cost_output": 15.0,
    "supports_vision": true,
    "supports_tools": true,
    "supports_caching": true,
    "deprecated": true,
    "deprecated_date": "2026-06-30",
    "replacement_model": "claude-sonnet-4-20250514"
  }
}
```

#### Updating Pricing

```json
{
  "gpt-4o": {
    "context": 128000,
    "cost_input": 2.0,  // Changed from 2.5
    "cost_output": 8.0,  // Changed from 10.0
    "supports_vision": true,
    "supports_tools": true,
    "supports_caching": true
  }
}
```

## Catalog Structure

### Top-Level Schema

```json
{
  "version": "1.0.0",           // Semver format
  "updated": "2026-02-06T06:00:00Z",  // ISO 8601 timestamp
  "providers": {
    "anthropic": { /* models */ },
    "openai": { /* models */ },
    "google": { /* models */ }
  }
}
```

### Model Metadata Fields

#### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `context` | integer | Context window in tokens | `200000` |
| `cost_input` | number | USD per 1M input tokens | `3.0` |
| `cost_output` | number | USD per 1M output tokens | `15.0` |

#### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `display_name` | string | UI display name | `"Claude 3 Haiku"` |
| `description` | string | Short description (≤50 chars) | `"BEST VALUE - cheapest"` |
| `category` | string | UI grouping category | `"Claude 3"` |
| `cost_cache_write` | number | Cache write cost per 1M tokens | `1.25` |
| `cost_cache_read` | number | Cache read cost per 1M tokens | `0.10` |
| `api_max_input` | integer | API input limit (if < context) | `200000` |
| `supports_vision` | boolean | Image input support | `true` |
| `supports_tools` | boolean | Function calling support | `true` |
| `supports_caching` | boolean | Prompt caching support | `true` |
| `reasoning_model` | boolean | Reasoning/o1-style model | `false` |
| `fixed_temperature` | number | Required temperature value | `1.0` |
| `deprecated` | boolean | Model is deprecated | `true` |
| `deprecated_date` | string | Deprecation date (YYYY-MM-DD) | `"2026-06-30"` |
| `replacement_model` | string | Recommended replacement | `"claude-sonnet-4"` |
| `free` | boolean | Free tier model | `false` |

## Model ID Conventions

### Rules

1. **Use dated IDs**: Always use provider's official dated model ID
   - ✅ Good: `claude-3-haiku-20240307`
   - ❌ Bad: `claude-haiku-latest`, `claude-haiku-4-5`

2. **Date format**: YYYYMMDD embedded in ID
   - ✅ Good: `gpt-4-turbo-2024-04-09`
   - ❌ Bad: `gpt-4-turbo` (no date)

3. **Provider format**: Follow provider's naming convention
   - Anthropic: `claude-{model}-{version}-YYYYMMDD`
   - OpenAI: `{model}-YYYY-MM-DD` or `{model}-preview`
   - AWS Bedrock: `provider.{model}-YYYYMMDD-v{version}:0`

### Exceptions

Some stable aliases are permitted:
- `gpt-4o`, `gpt-4o-mini` (OpenAI production aliases)
- `deepseek-chat`, `deepseek-reasoner` (official names)
- `gemini-2.5-pro`, `gemini-2.5-flash` (versioned aliases)

### Why Dated IDs?

- **Reproducibility**: Exact model version in logs
- **Deprecation tracking**: Easy to identify old models
- **No surprises**: Model behavior doesn't change unexpectedly
- **Provider compatibility**: Matches official provider APIs

## Deprecation Management

### Lifecycle Stages

1. **Active** - Model is available and recommended
2. **Deprecated** - Model still works but not recommended
3. **Retired** - Model no longer accessible (removed from catalog)

### Deprecation Process

**Step 1: Mark as deprecated**
```json
{
  "claude-3-5-sonnet-20241022": {
    "deprecated": true,
    "deprecated_date": "2026-06-30",
    "replacement_model": "claude-sonnet-4-20250514"
  }
}
```

**Step 2: UI warnings**
- Web UI shows warning when deprecated model selected
- CLI displays deprecation notice
- API response includes `deprecated: true` in metadata

**Step 3: Grace period**
- Typically 3-6 months after deprecation announcement
- Users migrate to replacement model

**Step 4: Removal**
- After grace period, remove from catalog
- Provider validator will detect as invalid

### Auto-Detection

The validator automatically detects deprecations:

```bash
# Run validator
python scripts/validate_catalog.py

# Validator fetches models from provider API
# Compares with catalog
# Reports models in catalog but not in API
```

## Validation & CI/CD

### Local Validation

```bash
# Validate catalog JSON
python scripts/validate_catalog.py

# Output:
# ✓ JSON syntax valid
# ✓ Schema validation passed
# ✓ Provider validation passed
# ✓ Found 1 providers with 5 models
# ✅ Catalog validation passed!
```

### Validation Rules

CI checks enforce:

1. ✅ JSON syntax is valid
2. ✅ Schema compliance (all required fields)
3. ✅ No duplicate model IDs per provider
4. ✅ Non-negative pricing values
5. ✅ Context window > 0
6. ✅ Dated model IDs (YYYYMMDD pattern)
7. ✅ Deprecated models have `deprecated_date`

### GitHub Actions CI

**Trigger:** PR that modifies `catalog/*.json`

**Workflow:**
1. Checkout code
2. Set up Python 3.10
3. Run `scripts/validate_catalog.py`
4. Check for dated model IDs
5. Report success/failure

**Example PR Check:**
```
✅ Validate Model Catalog
   - JSON syntax valid
   - Schema validation passed
   - Provider validation passed
   - Found 1 providers with 5 models
   - All models use dated IDs
```

## Auto-Sync System

### Overview

Weekly automated workflow to detect deprecated models:

1. **Fetch**: Get fresh model lists from provider APIs
2. **Compare**: Check catalog models vs API models
3. **Detect**: Find models in catalog but not in API
4. **Report**: Create PR with deprecation warnings
5. **Review**: Human reviews and merges PR

### Provider Validators

Each provider has a validator that fetches models:

```python
from stratifyai.utils.provider_validator import validate_provider_models

# Validate Anthropic models
result = validate_provider_models("anthropic", [
    "claude-3-haiku-20240307",
    "claude-3-5-sonnet-20241022"
])

print(result)
# {
#   "valid_models": ["claude-3-haiku-20240307"],
#   "invalid_models": ["claude-3-5-sonnet-20241022"],
#   "validation_time_ms": 450,
#   "error": None
# }
```

### Supported Providers

| Provider | Validator Method | API Endpoint |
|----------|-----------------|--------------|
| Anthropic | `models.list()` | Anthropic SDK |
| OpenAI | `models.list()` | OpenAI SDK |
| Google | `models.list()` | Google GenAI SDK |
| DeepSeek | `/v1/models` | OpenAI-compatible |
| Groq | `/openai/v1/models` | OpenAI-compatible |
| Grok | `/v1/models` | OpenAI-compatible |
| OpenRouter | `/api/v1/models` | Custom API |
| Ollama | `/api/tags` | Local API |
| AWS Bedrock | `list_foundation_models()` | boto3 |

## FAQ

### Q: How often should I update the catalog?

**A:** Update when:
- New model released (within 1 week)
- Pricing changes (immediately)
- Deprecation announced (same day)
- Capability changes (within 1 week)

### Q: What if I don't know all the model fields?

**A:** Only `context`, `cost_input`, and `cost_output` are required. Other fields are optional. Submit with what you know, and others can fill in details later.

### Q: How do I find official pricing?

**A:** Provider pricing pages:
- Anthropic: https://www.anthropic.com/pricing
- OpenAI: https://openai.com/api/pricing/
- Google: https://ai.google.dev/pricing
- DeepSeek: https://platform.deepseek.com/pricing
- Groq: https://wow.groq.com/
- Grok/X.AI: https://x.ai/api

### Q: What if my PR fails CI?

**A:** Check the error message:
- **JSON syntax**: Fix JSON formatting
- **Missing required field**: Add `context`, `cost_input`, or `cost_output`
- **Duplicate model ID**: Remove duplicate entry
- **Invalid pricing**: Ensure all costs ≥ 0
- **No dated ID**: Use provider's official dated model ID

### Q: Can I add hypothetical/future models?

**A:** No. Only add models that currently exist in provider APIs. Wait for official release.

### Q: How do I test my changes locally?

**A:**
```bash
# 1. Validate catalog
python scripts/validate_catalog.py

# 2. Test catalog loading
python -c "
from stratifyai.catalog_manager import get_anthropic_models
models = get_anthropic_models()
print(f'Loaded {len(models)} models')
print(list(models.keys()))
"

# 3. Run API server and test
source .venv/bin/activate
python api/main.py
# Visit http://localhost:8000 and check dropdown
```

### Q: What's the approval process?

**A:** 
1. Submit PR with supporting documentation (pricing page link, announcement)
2. CI automatically validates
3. Maintainer reviews for accuracy
4. Merged if CI passes + maintainer approves
5. Typically merged within 24-48 hours

## Getting Help

- 📖 **Read first**: `catalog/README.md`
- 🔍 **Check examples**: `catalog/models.json`
- 🐛 **Report issues**: GitHub Issues
- 💬 **Ask questions**: GitHub Discussions
- 📧 **Contact**: agent@warp.dev

## Changelog

### v1.0.0 (February 6, 2026)
- Initial catalog externalization
- JSON schema validation
- CI/CD automation
- Community contribution guidelines
- Provider validator enhancements
- Deprecation tracking system

---

**Maintained by:** StratifyAI Community  
**License:** MIT  
**Contributing:** See `catalog/README.md`
