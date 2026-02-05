# 1M Context Models - Labels & Dynamic Validation

## Overview
StratifyAI now has comprehensive 1M context model labels across all UIs (CLI, Interactive, Web UI). The labeling system is **dynamic** - it validates models at runtime and merges static metadata with provider APIs.

## Updates Made (February 5, 2026)

### Added/Updated Labels
1. **Google Gemini models** - Added "1M context" labels to descriptions
2. **OpenRouter models** - Enhanced with 1M context indicators
3. **New category** - "1M Context Models" for OpenRouter
4. **Free tier highlight** - "Free Models (1M Context)" category

### OpenRouter Curated List Expanded
- **Before**: 7 models
- **After**: 11 models (4 new 1M context models added)
- New additions:
  - `anthropic/claude-opus-4-5` - Premium quality, 1M context
  - `google/gemini-2.5-pro` - Best quality, 1M context
  - `google/gemini-3` - Latest Google, 1M context
  - `google/gemini-2.0-flash-exp:free` - FREE 1M context

## Complete List of 1M Context Models

### Direct Providers

#### Anthropic (`provider: anthropic`)
| Model ID | Display Name | Context | API Limit | Description |
|----------|--------------|---------|-----------|-------------|
| `claude-opus-4-5` | Claude Opus 4.5 | **1M** | 200k input | Premium quality, 1M context |
| `claude-opus-4-5-20251101` | Claude Opus 4.5 | **1M** | 200k input | Dated version |

**Note**: Despite 1M context, Anthropic API enforces 200k input limit. Use chunking!

#### Google (`provider: google`)
| Model ID | Display Name | Context | API Limit | Description |
|----------|--------------|---------|-----------|-------------|
| `gemini-2.5-pro` | Gemini 2.5 Pro | **1M** | No limit | Best quality, 1M context |
| `gemini-2.5-flash` | Gemini 2.5 Flash | **1M** | No limit | BEST VALUE - 1M context, fast/cheap |
| `gemini-2.5-flash-lite` | Gemini 2.5 Flash Lite | **1M** | No limit | FREE tier option |

**Note**: Google Gemini has NO artificial input limits - full 1M usable!

### OpenRouter (`provider: openrouter`)

#### Premium 1M Models
| Model ID | Display Name | Context | Description |
|----------|--------------|---------|-------------|
| `anthropic/claude-opus-4-5` | Claude Opus 4.5 | **1M** | Premium quality, 1M context |
| `google/gemini-3` | Gemini 3 | **1M** | Latest Google, 1M context |
| `google/gemini-2.5-pro` | Gemini 2.5 Pro | **1M** | Best quality, 1M context |
| `google/gemini-2.5-flash` | Gemini 2.5 Flash | **1M** | BEST VALUE - 1M context, fast/cheap |

#### Free 1M Models
| Model ID | Display Name | Context | Description |
|----------|--------------|---------|-------------|
| `google/gemini-2.5-flash-lite` | Gemini 2.5 Flash Lite | **1M** | FREE - 1M context |
| `google/gemini-2.0-flash-exp:free` | Gemini 2.0 Flash Exp | **1M** | FREE - 1M context, vision/tools |

#### Large Context Models (500k+)
| Model ID | Display Name | Context | Description |
|----------|--------------|---------|-------------|
| `meta-llama/llama-4-maverick:free` | Llama 4 Maverick | **512k** | FREE - vision/tools |
| `meta-llama/llama-4-scout:free` | Llama 4 Scout | **512k** | FREE - vision/tools |

## How Dynamic Labels Work

### 1. Static Configuration
Labels are defined in `stratifyai/config.py`:
```python
INTERACTIVE_GOOGLE_MODELS = {
    "gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro",
        "description": "Best quality, 1M context",  # ← Static label
        "category": "Gemini 2.5",
    },
}
```

### 2. Model Validation (Runtime)
The `provider_validator.py` module validates models at runtime:
```python
def get_validated_interactive_models(provider: str):
    # 1. Get curated model list
    model_ids = list(interactive_models.keys())
    
    # 2. Validate with provider API
    validation_result = validate_provider_models(provider, model_ids)
    
    # 3. Merge static labels + validated models
    for model_id in validation_result["valid_models"]:
        models[model_id] = {
            **full_config,      # Cost, context, features from MODEL_CATALOG
            **interactive_meta, # Display name, description, category (labels!)
        }
```

### 3. UI Display (All Interfaces)
All UIs automatically get dynamic labels:

**CLI/Interactive Mode**:
```
Available anthropic models:
  ── Claude 4.5 (Latest) ──
  1. Claude Opus 4.5 - Premium quality, 1M context
  2. Claude Sonnet 4.5 - Latest flagship, best balance
```

**Web UI**:
```html
<optgroup label="1M Context Models">
  <option>Claude Opus 4.5 - Premium quality, 1M context</option>
  <option>Gemini 2.5 Pro - Best quality, 1M context</option>
</optgroup>
```

## Label Consistency Across UIs

| UI Type | Source | Dynamic? | Context Labels |
|---------|--------|----------|----------------|
| CLI chat mode | `INTERACTIVE_*_MODELS` | ✅ Yes | ✅ All present |
| Interactive mode | `INTERACTIVE_*_MODELS` | ✅ Yes | ✅ All present |
| Web UI | API → `INTERACTIVE_*_MODELS` | ✅ Yes | ✅ All present |

All three UIs use the **same source** (`INTERACTIVE_*_MODELS`), so labels are **100% consistent**.

## Validation Process

### Real-time Validation
```
User selects provider → System validates models → Shows only available models
     ↓                           ↓                            ↓
  "anthropic"            API: models.list()        Claude Opus 4.5 ✓
                         (checks availability)      Claude Haiku 4.5 ✓
                                                    old-model-xyz ✗ (hidden)
```

### Validation Results Display
```
✓ Validated 5 models (245ms)
⚠️ Unavailable: gpt-4, claude-3
⚠️ Default models displayed. Could not validate models.
```

## Categories for 1M Models

### New Categories Added
1. **"1M Context Models"** - Premium large-context models (OpenRouter)
2. **"Free Models (1M Context)"** - Free tier with 1M context
3. **"Claude 4.5 (Latest)"** - Includes 1M Opus model
4. **"Gemini 2.5"** - All have 1M context

### Category Hierarchy
```
Premium Models
  ├── Claude Sonnet 4.5 (200k)
  ├── GPT-4o (128k)
  └── Gemini 2.5 Flash - 1M context

1M Context Models
  ├── Claude Opus 4.5 - 1M context
  ├── Gemini 2.5 Pro - 1M context
  └── Gemini 3 - 1M context

Free Models (1M Context)
  ├── Gemini 2.5 Flash Lite
  └── Gemini 2.0 Flash Exp
```

## Cost Comparison (1M Context Models)

### Paid Models (per 1M tokens)
| Model | Provider | Input Cost | Output Cost | Best For |
|-------|----------|------------|-------------|----------|
| Claude Opus 4.5 | Anthropic | $5.00 | $25.00 | Premium quality |
| Gemini 2.5 Pro | Google | $1.25 | $5.00 | Best value paid |
| Gemini 2.5 Flash | Google | $0.075 | $0.30 | Speed & cost |
| Gemini 3 | Google | $2.50 | $10.00 | Latest features |

### Free Models (1M context)
- **Gemini 2.5 Flash Lite** - $0/$0 ✨
- **Gemini 2.0 Flash Exp** - $0/$0 ✨

## User Benefits

### Before
```
❌ Users had to guess which models had 1M context
❌ No consistent labeling across UIs
❌ Missing models in OpenRouter list
```

### After
```
✅ Clear "1M context" labels on all relevant models
✅ Consistent across CLI, Interactive, and Web UI
✅ 11 curated OpenRouter models (was 7)
✅ Dedicated "1M Context Models" category
✅ Free 1M models clearly marked
```

## Implementation Details

### Files Modified
1. `stratifyai/config.py` (Lines 1069-1208)
   - Enhanced descriptions with "1M context" labels
   - Added 4 new models to OpenRouter curated list
   - Created new category "1M Context Models"

2. `stratifyai/utils/provider_validator.py` (Lines 359-442)
   - No changes needed - already merges labels dynamically
   - Validates models at runtime
   - Returns combined metadata

### Zero Breaking Changes
- ✅ Backward compatible - only added labels
- ✅ No API changes
- ✅ No breaking config changes
- ✅ Existing code continues to work

## Testing

### CLI Testing
```bash
# Test interactive mode with 1M models
stratifyai interactive --provider anthropic
# Select Claude Opus 4.5 - should show "Premium quality, 1M context"

stratifyai interactive --provider google
# Should show three 1M models with labels
```

### Web UI Testing
1. Start server: `python -m uvicorn api.main:app --reload --port 8080`
2. Navigate to `http://localhost:8080`
3. Select `anthropic` provider
4. Verify "Claude Opus 4.5 - Premium quality, 1M context" appears
5. Select `openrouter` provider
6. Verify "1M Context Models" category with 4 models

### Expected Results
- ✅ All 1M models show "1M context" in description
- ✅ Categories group models logically
- ✅ Free models clearly marked "FREE"
- ✅ Validation shows "✓ Validated X models"
- ✅ Labels consistent across all three UIs

## Future Enhancements

### Potential Improvements
1. **Dynamic context display** - Show actual context window in model list
2. **Context usage indicator** - Real-time token counter in UI
3. **Smart recommendations** - Suggest 1M models when file is large
4. **Context limit warnings** - Alert when approaching limits
5. **Auto-chunking suggestion** - Prompt to enable chunking for large files

### Model Additions
- Monitor for new 1M+ context models from providers
- Update labels when models are upgraded
- Add more free tier options as they become available

## Related Documentation
- `WEB_UI_CHUNKING_IMPLEMENTATION.md` - Chunking feature for large files
- `TEMPERATURE_IMPLEMENTATION_SUMMARY.md` - Temperature controls
- `stratifyai/config.py` - Model catalog and labels
- `stratifyai/utils/provider_validator.py` - Dynamic validation
