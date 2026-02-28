# Model Catalog

This directory contains the LLM model catalog for StratifyAI. The catalog is externalized as JSON to enable community contributions and automated synchronization.

## Structure

- **`models.json`** - Main model catalog with pricing, capabilities, and metadata
- **`schema.json`** - JSON schema for validation
- **`README.md`** - This file (contribution guidelines)

## Contributing

We welcome community contributions to keep the model catalog up-to-date!

### When to Submit a PR

- **New model release**: Provider added a new model
- **Price change**: Model pricing was updated
- **Model deprecation**: Provider announced a model will be retired
- **Capability update**: Model gained new features (vision, tools, etc.)
- **Correction**: Existing catalog entry has incorrect information

### Submission Guidelines

1. **Use dated model IDs**: Always use provider's official dated model ID (e.g., `claude-3-haiku-20240307`), NOT aliases like `claude-haiku-latest`
   
2. **Required fields**:
   ```json
   {
     "context": 200000,           // Context window in tokens
     "cost_input": 3.0,           // USD per 1M input tokens
     "cost_output": 15.0          // USD per 1M output tokens
   }
   ```

3. **Optional but recommended**:
   ```json
   {
     "display_name": "Claude 3 Haiku",
     "description": "Fast & affordable",
     "category": "Claude 3",
     "supports_vision": true,
     "supports_tools": true,
     "supports_caching": false,
     "cost_cache_write": 1.25,
     "cost_cache_read": 0.10
   }
   ```

4. **For deprecations**:
   ```json
   {
     "deprecated": true,
     "deprecated_date": "2026-06-30",
     "replacement_model": "claude-sonnet-4-20250514"
   }
   ```

### PR Process

1. **Fork** the repository
2. **Edit** `catalog/models.json`
3. **Validate** your changes:
   ```bash
   python scripts/validate_catalog.py
   ```
4. **Commit** with a descriptive message:
   ```
   catalog: Add claude-opus-4-6-20260205
   
   - Added new Claude Opus 4.6 model (released Feb 5, 2026)
   - Context: 200K tokens
   - Pricing: $5 input / $25 output per 1M tokens
   - Source: https://www.anthropic.com/news/claude-opus-4-6
   ```
5. **Submit PR** with supporting documentation (pricing page link, announcement, etc.)

### Validation Rules

The CI workflow will automatically check:

- ✅ JSON is valid and matches `schema.json`
- ✅ All required fields are present
- ✅ No duplicate model IDs within provider
- ✅ Pricing values are non-negative
- ✅ Context window > 0
- ✅ Model ID follows pattern (dated IDs preferred)

### Sources of Truth

When adding/updating models, use these official sources:

- **OpenAI**: https://openai.com/api/pricing/
- **Anthropic**: https://www.anthropic.com/pricing
- **Google**: https://ai.google.dev/pricing
- **DeepSeek**: https://platform.deepseek.com/pricing
- **Groq**: https://wow.groq.com/
- **Grok/X.AI**: https://x.ai/api
- **OpenRouter**: https://openrouter.ai/models
- **AWS Bedrock**: https://aws.amazon.com/bedrock/pricing/

### Auto-Sync

StratifyAI has a **weekly auto-sync workflow** that:

1. Fetches model lists from provider APIs
2. Detects deprecated models (in catalog but not in API)
3. Creates a PR with deprecation warnings
4. Requires human review before merging

This helps catch deprecations early, but **manual contributions are still valuable** for:
- Pricing updates (APIs don't expose pricing)
- New model announcements (before API availability)
- Capability metadata (vision, tools, caching)

## Need Help?

- 📖 See examples in `models.json`
- 🐛 Report issues: GitHub Issues
- 💬 Ask questions: GitHub Discussions
- 📧 Contact: agent@warp.dev

## License

The model catalog is released under MIT License. Contributions are subject to the same license.
