# Enhanced Token Limit Error Handling

## Overview
StratifyAI now provides intelligent, user-friendly error messages when content exceeds model token limits. The system proactively detects token limit issues **before** making API calls and provides contextual suggestions based on the specific scenario.

## Updates Made (February 5, 2026)

### Backend Changes (`api/main.py`)
1. **Proactive Token Validation** (Lines 321-382)
   - Estimates tokens before API call using `count_tokens_for_messages()`
   - Checks against model's context window and API input limits
   - Three-tier validation system:
     - System maximum (1M tokens)
     - API input limits (e.g., Claude's 200k)
     - Model context limits

2. **Smart Error Messages**
   - Distinguishes between API limits vs model limits
   - Provides token counts with formatting (223,012 tokens)
   - Indicates whether chunking is already enabled
   - Suggests specific models by name

3. **Fallback Error Handling** (Lines 451-515)
   - Catches provider API errors that slip through
   - Extracts token counts from error messages using regex
   - Provides same smart suggestions as proactive validation

### Frontend Changes (`api/static/index.html`)
1. **Enhanced Error Display** (Lines 887-909)
   - Detects structured error responses
   - Displays error title, message, and suggestions
   - Shows chunking tip if not already enabled
   - Formats with emojis for visual clarity

## Error Scenarios & Messages

### Scenario 1: API Input Limit (Model Has Larger Context)
**Example**: Claude Opus 4.5 - 223k tokens input, 200k API limit, 1M context window

**Error Message**:
```
📊 Input Too Large

Input is too long for claude-opus-4-5. The content has approximately 
223,012 tokens, but the API restricts input to 200,000 tokens (despite 
the model's 1,000,000 token context window).

💡 Suggestions:
✓ Enable 'Smart Chunking' checkbox to reduce tokens by 40-90%
✓ Switch to Google Gemini models (no API input limits): gemini-2.5-pro, 
  gemini-2.5-flash
✓ Switch to OpenRouter with google/gemini-2.5-pro or google/gemini-2.5-flash

⚠️ TIP: Enable the 'Smart Chunking' checkbox below the file upload to 
automatically reduce token usage by 40-90%.
```

### Scenario 2: Model Context Limit (Model Can't Handle Input)
**Example**: GPT-4o - 150k tokens input, 128k context limit

**Error Message**:
```
📊 Input Too Large

Input is too long for gpt-4o. The content has approximately 150,000 
tokens, which exceeds the model's maximum of 128,000 tokens.

💡 Suggestions:
✓ Switch to a model with larger context window:
  - Google Gemini 2.5 Pro (1M tokens, no API limits)
  - Google Gemini 2.5 Flash (1M tokens, cheaper)
  - Claude Opus 4.5 (1M context, 200k API limit)
✓ Enable 'Smart Chunking' to reduce token usage

⚠️ TIP: Enable the 'Smart Chunking' checkbox below the file upload to 
automatically reduce token usage by 40-90%.
```

### Scenario 3: System Maximum Exceeded
**Example**: 1.5M tokens input (exceeds system's 1M limit)

**Error Message**:
```
🚫 File Too Large

File is too large to process. The content has approximately 1,500,000 
tokens, which exceeds the system's maximum limit of 1,000,000 tokens.

Please split your file into smaller chunks or use a different processing 
approach.
```

### Scenario 4: Provider API Error (Fallback)
**Example**: Error slips through proactive validation

**Error Message**:
```
📊 Input Too Large

[anthropic] Chat completion failed: Error code: 400 - 
{'type': 'error', 'error': {'type': 'invalid_request_error', 
'message': 'prompt is too long: 223001 tokens > 200000 maximum'}}

💡 Suggestions:
✓ Enable 'Smart Chunking' checkbox to reduce tokens by 40-90%
✓ Switch to Google Gemini models (no API input limits): gemini-2.5-pro, 
  gemini-2.5-flash
✓ Your input: 223,001 tokens | API limit: 200,000 tokens | 
  Model context: 1,000,000 tokens

⚠️ TIP: Enable the 'Smart Chunking' checkbox below the file upload to 
automatically reduce token usage by 40-90%.
```

## Technical Implementation

### Token Estimation Process
```python
# 1. Estimate tokens from messages
from stratifyai.utils.token_counter import count_tokens_for_messages
estimated_tokens = count_tokens_for_messages(messages, provider, model)

# 2. Get model limits from catalog
context_window = get_context_window(provider, model)
api_max_input = MODEL_CATALOG[provider][model].get("api_max_input")
effective_limit = api_max_input if api_max_input else context_window

# 3. Validate against limits
if estimated_tokens > 1_000_000:
    raise HTTPException(413, "content_too_large")
elif estimated_tokens > effective_limit:
    if api_max_input and context_window > api_max_input:
        raise HTTPException(413, "input_too_long", suggestion="Enable chunking...")
    else:
        raise HTTPException(413, "input_too_long", suggestion="Switch to larger model...")
```

### Provider-Specific Token Estimation
| Provider | Method | Formula |
|----------|--------|---------|
| OpenAI | tiktoken (cl100k_base) | Exact encoding |
| Anthropic | Character-based | ~3.5 chars/token |
| Google | Character-based | ~4.0 chars/token |
| DeepSeek/Groq/Grok | tiktoken (cl100k_base) | Exact encoding |
| OpenRouter | tiktoken (cl100k_base) | Exact encoding |
| Ollama | Character-based | ~4.0 chars/token |

### Model Limits Reference
| Provider | Model | Context | API Limit | Notes |
|----------|-------|---------|-----------|-------|
| Anthropic | Claude Opus 4.5 | 1M | **200k** | API restricts input |
| Anthropic | Claude Sonnet 4.5 | 200k | 200k | No restriction |
| Google | Gemini 2.5 Pro | 1M | **None** | Full 1M usable |
| Google | Gemini 2.5 Flash | 1M | **None** | Full 1M usable |
| OpenAI | GPT-4o | 128k | 128k | No restriction |
| OpenAI | o1 | 200k | 200k | No restriction |
| DeepSeek | Reasoner R1 | 64k | 64k | No restriction |

## Error Response Structure

### HTTP Status Codes
- **413 Payload Too Large** - Content exceeds token limits
- **400 Bad Request** - Invalid parameters (temperature, etc.)
- **401 Unauthorized** - Authentication issues
- **402 Payment Required** - Insufficient balance
- **404 Not Found** - Model not found
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Unexpected errors

### JSON Response Format
```json
{
  "detail": {
    "error": "input_too_long",
    "message": "Input is too long for claude-opus-4-5. The content has approximately 223,012 tokens...",
    "estimated_tokens": 223012,
    "api_limit": 200000,
    "context_window": 1000000,
    "provider": "anthropic",
    "model": "claude-opus-4-5",
    "suggestion": "✓ Enable 'Smart Chunking' checkbox to reduce tokens by 40-90%\n✓ Switch to Google Gemini models...",
    "chunking_enabled": false
  }
}
```

## User Experience Improvements

### Before Enhancement
```
❌ Generic error: "prompt is too long: 223001 tokens > 200000 maximum"
❌ No explanation of why or what to do
❌ User must research model limits and solutions
❌ No indication that chunking feature exists
```

### After Enhancement
```
✅ Clear title: "📊 Input Too Large"
✅ Explains the issue with token counts and limits
✅ Distinguishes API limits from model context
✅ Suggests specific models by name (gemini-2.5-pro)
✅ Highlights chunking feature with reduction percentage
✅ Shows whether chunking is already enabled
✅ Provides multiple solution paths
```

## Suggested Models for Large Content

### No API Input Limits (Full 1M Context)
1. **Google Gemini 2.5 Pro** - Best quality, $1.25/1M input tokens
2. **Google Gemini 2.5 Flash** - BEST VALUE, $0.075/1M input tokens
3. **Google Gemini 2.5 Flash Lite** - FREE tier, 1M context

### Large Context with API Limits
1. **Claude Opus 4.5** - Premium quality, 1M context (200k API limit)
   - Use with chunking for 223k+ token files
2. **Claude Sonnet 4.5** - Balanced, 200k context (no API limit)

### Via OpenRouter (Unified API)
1. `google/gemini-2.5-pro` - 1M context, no limits
2. `google/gemini-2.5-flash` - 1M context, no limits
3. `anthropic/claude-opus-4-5` - 1M context, 200k API limit

## Chunking Integration

### Automatic Suggestion
When token limit is exceeded, the system:
1. Checks if chunking is already enabled
2. If not, displays tip: "Enable the 'Smart Chunking' checkbox..."
3. Shows expected reduction: "40-90% token reduction"

### Expected Token Reductions
| File Type | Strategy | Reduction | Example |
|-----------|----------|-----------|---------|
| CSV | Schema extraction | 80-99% | 223k → 2k-45k |
| JSON | Schema extraction | 78-95% | 223k → 11k-49k |
| Logs | Error extraction | 90% | 223k → 22k |
| Code | Structure extraction | 33-80% | 223k → 45k-149k |

### Usage Flow
1. User uploads 223k token file to Claude Opus 4.5
2. System detects: 223k > 200k API limit
3. Error displayed with chunking suggestion
4. User enables "Smart Chunking" checkbox
5. System reduces to ~22k-89k tokens (fits within limit)
6. Request succeeds

## Testing

### Manual Testing Steps
1. **Start Web UI**:
   ```bash
   source .venv/bin/activate
   python -m uvicorn api.main:app --reload --port 8080
   ```

2. **Test Scenario 1 - Claude Opus 4.5 with large file**:
   - Navigate to http://localhost:8080
   - Select provider: `anthropic`
   - Select model: `claude-opus-4-5`
   - Upload file with >200k tokens (or paste ~700k+ characters)
   - Submit without chunking
   - **Expected**: Enhanced error with chunking suggestion

3. **Test Scenario 2 - Enable chunking**:
   - Same setup as above
   - Enable "Smart Chunking" checkbox
   - Submit again
   - **Expected**: Request succeeds with reduced tokens

4. **Test Scenario 3 - Switch to Gemini**:
   - Same large file
   - Select provider: `google`
   - Select model: `gemini-2.5-flash`
   - Submit without chunking
   - **Expected**: Request succeeds (no API limit)

### Automated Tests
```python
# Test token estimation
def test_token_validation():
    from stratifyai.utils.token_counter import estimate_tokens
    
    # 223k token content for Anthropic
    content = 'A' * (223000 * 3.5)  # 3.5 chars/token
    tokens = estimate_tokens(content, 'anthropic', 'claude-opus-4-5')
    
    assert tokens > 200000, "Should exceed API limit"
    assert tokens < 1000000, "Should be under model context"

# Test error handling
async def test_error_handling():
    client = LLMClient(provider='anthropic')
    large_message = Message(role='user', content='A' * 800000)
    
    with pytest.raises(HTTPException) as exc:
        await chat_completion(
            ChatCompletionRequest(
                provider='anthropic',
                model='claude-opus-4-5',
                messages=[{'role': 'user', 'content': large_message.content}]
            )
        )
    
    assert exc.value.status_code == 413
    assert 'input_too_long' in str(exc.value.detail)
    assert 'Smart Chunking' in str(exc.value.detail)
```

## Configuration

### Adjustable Limits
The system has three configurable limits:

1. **System Maximum** (Hardcoded):
   ```python
   MAX_SYSTEM_LIMIT = 1_000_000  # 1M tokens
   ```

2. **Model Context Window** (From `MODEL_CATALOG`):
   ```python
   "claude-opus-4-5": {
       "context": 1000000,  # Model capability
       ...
   }
   ```

3. **API Input Limit** (From `MODEL_CATALOG`):
   ```python
   "claude-opus-4-5": {
       "api_max_input": 200000,  # API restriction
       ...
   }
   ```

### Adding New Model Limits
To add API input limits for new models:
```python
# In stratifyai/config.py
MODEL_CATALOG = {
    "provider": {
        "model-name": {
            "context": 1000000,
            "api_max_input": 200000,  # Add this field
            ...
        }
    }
}
```

## Future Enhancements

### Potential Improvements
1. **Progressive Chunking** - Automatically enable chunking if token limit exceeded
2. **Model Recommendations** - Rank suggested models by cost/quality/speed
3. **Token Usage Preview** - Show estimated tokens before submission
4. **Dynamic Chunk Size** - Auto-calculate optimal chunk size for file
5. **Cost Comparison** - Show cost differences between suggested models
6. **Token Counter Widget** - Real-time token counter in UI
7. **Smart Model Selection** - Auto-switch to appropriate model based on file size

### Monitoring & Analytics
Track error patterns to improve suggestions:
- Which errors are most common?
- Do users follow suggestions?
- Which alternative models are chosen?
- How often is chunking enabled after error?

## Related Documentation
- `WEB_UI_CHUNKING_IMPLEMENTATION.md` - Chunking feature details
- `1M_CONTEXT_MODELS_SUMMARY.md` - Large context model catalog
- `stratifyai/utils/token_counter.py` - Token estimation utilities
- `stratifyai/config.py` - Model limits configuration
- `api/main.py` - Error handling implementation
