# Vision Error Handling Improvements

## Date
February 5, 2026

## Issue
Users were getting unfriendly API errors when trying to use images with non-vision models:
```
Error: Chat completion failed: Error code: 400 - {'error': {'message': 'Invalid content type. 
image_url is only supported by certain models.', 'type': 'invalid_request_error', 'param': 
'messages.[0].content.[1].type', 'code': None}}
```

## Root Cause
1. **Config Error:** `gpt-4-turbo` was incorrectly marked as `supports_vision: True`
2. **Unfriendly API Errors:** When vision validation was bypassed or failed, raw API errors were shown to users

## Solutions Implemented

### 1. Fixed Config (✅ COMPLETE)
**File:** `stratifyai/config.py`

**Changes:**
- `OPENAI_MODELS["gpt-4-turbo"]["supports_vision"]` → `False` (line 32)
- `INTERACTIVE_OPENAI_MODELS["gpt-4-turbo"]["description"]` → "Legacy flagship, tools support" (line 1052)

**Result:** CLI will now block image uploads for `gpt-4-turbo` with clear message:
```
✗ Vision not supported: gpt-4-turbo cannot process image files
⚠️ Please select a vision-capable model
```

---

### 2. Added User-Friendly Error Handling (✅ COMPLETE)
**Files Modified:** 3 provider files

#### OpenAI Provider
**File:** `stratifyai/providers/openai.py` (lines 168-176, 256-264)

**Error Detection:**
- Checks for `"image_url is only supported by certain models"` or `"Invalid content type"`

**Friendly Message:**
```
Vision not supported: The model 'gpt-4-turbo' cannot process images. 
Please use a vision-capable model like 'gpt-4o' or 'gpt-4o-mini'.
```

#### Anthropic Provider
**File:** `stratifyai/providers/anthropic.py` (lines 166-174, 250-258)

**Error Detection:**
- Checks for `"image"` + `"not supported"` or `"invalid"`

**Friendly Message:**
```
Vision not supported: The model 'claude-3-5-haiku-20241022' cannot process images. 
Please use a vision-capable Claude model like 'claude-sonnet-4-5' or 'claude-opus-4-5'.
```

#### OpenAICompatibleProvider (Google, OpenRouter, Ollama)
**File:** `stratifyai/providers/openai_compatible.py` (lines 170-177, 183-191, 291-298, 304-312)

**Error Detection:**
- Checks for `"image"` + (`"not supported"` or `"invalid"` or `"image_url"`)

**Friendly Message:**
```
Vision not supported: The model '{model}' cannot process images. 
Please use a vision-capable model (e.g., gemini-2.5-pro for Google, gpt-4o for OpenAI via OpenRouter).
```

---

## Before vs After

### Before
```
You: describe the image
Error:  Chat completion failed: Error code: 400 - {'error': {'message': 'Invalid content type. 
image_url is only supported by certain models.', 'type': 'invalid_request_error', 'param': 
'messages.[0].content.[1].type', 'code': None}}
```

### After (CLI Validation)
```
File path (or press Enter to skip) (): data/hawk.jpg
✗ Vision not supported: gpt-4-turbo cannot process image files
⚠️ Please select a vision-capable model
```

### After (API Error - if validation bypassed)
```
You: describe the image
Error: Vision not supported: The model 'gpt-4-turbo' cannot process images. 
Please use a vision-capable model like 'gpt-4o' or 'gpt-4o-mini'.
```

---

## Error Handling Strategy

### Layer 1: Client-Side Validation (Primary Defense)
- **Location:** CLI (`stratifyai_cli.py` lines 338-344, 842-848)
- **Method:** Check `MODEL_CATALOG[provider][model]["supports_vision"]` before upload
- **Benefit:** Catches errors before API call, saves costs

### Layer 2: Provider Error Handling (Fallback)
- **Location:** All vision-capable providers (OpenAI, Anthropic, OpenAICompatibleProvider, Bedrock)
- **Method:** Parse API error messages and provide friendly alternatives
- **Benefit:** Handles edge cases, API changes, or validation bypasses

---

## Testing

### Test Scenario 1: Non-vision model in CLI
```bash
$ stratifyai chat --provider openai --model gpt-4-turbo
File path: data/hawk.jpg
✗ Vision not supported: gpt-4-turbo cannot process image files
⚠️ Please select a vision-capable model
```
**Result:** ✅ Blocks at CLI level

### Test Scenario 2: API error fallback
If somehow validation is bypassed:
```
Error: Vision not supported: The model 'gpt-4-turbo' cannot process images. 
Please use a vision-capable model like 'gpt-4o' or 'gpt-4o-mini'.
```
**Result:** ✅ Friendly error message

---

## Coverage

### Providers with Friendly Vision Errors
- ✅ OpenAI (`stratifyai/providers/openai.py`)
- ✅ Anthropic (`stratifyai/providers/anthropic.py`)
- ✅ Google/OpenRouter/Ollama (`stratifyai/providers/openai_compatible.py`)
- ⏭️ Bedrock - already has validation error handling (lines 166-177, 243-253)

### Vision-Capable Models (No Errors Expected)
- OpenAI: `gpt-4o`, `gpt-4o-mini` ✅
- Anthropic: All Claude 3/3.5/4/4.5 (except one haiku variant) ✅
- Google: `gemini-2.5-pro`, `gemini-2.5-flash` ✅
- Bedrock: Claude + Nova models ✅
- OpenRouter: Multiple vision models ✅

---

## Summary

**Problem:** Confusing API errors when using images with non-vision models  
**Solution 1:** Fixed config to correctly mark `gpt-4-turbo` as non-vision  
**Solution 2:** Added friendly error messages in all vision-capable providers  
**Result:** Users get clear, actionable error messages instead of raw API errors  

**Files Changed:** 4
1. `stratifyai/config.py` - Fixed vision flags
2. `stratifyai/providers/openai.py` - Added friendly errors
3. `stratifyai/providers/anthropic.py` - Added friendly errors
4. `stratifyai/providers/openai_compatible.py` - Added friendly errors

**Lines Changed:** ~60 lines total
