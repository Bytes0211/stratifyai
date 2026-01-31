# Error Handling Examples

This document describes the improved error handling in the StratumAI GUI.

## Features Added

### 1. Visual Error Display
- Errors now appear in red boxes with clear headings
- Detailed error information is shown in a collapsible format
- Error messages don't pollute the conversation history

### 2. Categorized Error Types

#### ❌ Temperature Not Supported
**Trigger**: When a reasoning model receives an unsupported temperature value
**Example**: Using temperature=0.5 with o1, o3, or deepseek-reasoner models
**Display**:
```
Main message (red box):
o1-mini does not support temperature 0.5. The default value is 1.0.

Details (white monospace box):
[openai] Chat completion failed: Error code: 400 - {'error': {'message': "Unsupported value: 'temperature' does not support 0.5 with this model. Only the default (1) value is supported.", 'type': 'invalid_request_error', 'param': 'temperature', 'code': 'unsupported_value'}}
```

**Note**: The main message and technical details are displayed in separate sections for clarity.

#### 🔑 Authentication Error
**Trigger**: Missing or invalid API key
**Example**: OPENAI_API_KEY not set in .env file
**Display**:
```
🔑 Authentication Error
---
API key is missing or invalid for openai.

Error: [openai] API key not provided

Please check your .env file.
```

#### ⏱️ Rate Limit Exceeded
**Trigger**: Too many requests to provider API
**Example**: Hitting OpenAI rate limits
**Display**:
```
⏱️ Rate Limit Exceeded
---
Too many requests to openai.

Error: Rate limit reached for requests...

Please wait a moment and try again.
```

#### 🔍 Model Not Found
**Trigger**: Requesting a model that doesn't exist
**Example**: Using an invalid model name
**Display**:
```
🔍 Model Not Found
---
The model "gpt-5-ultra" is not available.

Error: Invalid model specified...
```

#### 🌐 Connection Error
**Trigger**: Network issues or server not running
**Example**: FastAPI server is down
**Display**:
```
🌐 Connection Error
---
Failed to communicate with the API.

Error: Failed to fetch

Please check if the server is running.
```

### 3. Structured API Error Responses

The API now returns structured error responses with:
- **error**: Error type (authentication_error, rate_limit_error, etc.)
- **detail**: Detailed error message
- **provider**: Provider that caused the error
- **model**: Model that was being used

Example API response:
```json
{
  "error": "invalid_parameter_error",
  "detail": "[openai] Chat completion failed: Error code: 400...",
  "provider": "openai",
  "model": "o1-mini"
}
```

## Frontend Changes

### CSS Additions
```css
.message.error {
    background: #fee;
    border: 1px solid #fcc;
    color: #c33;
    max-width: 100%;
}

.error-details {
    font-size: 12px;
    margin-top: 8px;
    padding: 8px;
    background: #fff;
    border-radius: 4px;
    font-family: monospace;
    white-space: pre-wrap;
    word-break: break-word;
}
```

### JavaScript Enhancements
- Added `addMessage()` details parameter for error information
- Enhanced error parsing with pattern matching
- Improved error categorization
- Error messages excluded from conversation history

## Backend Changes

### Error Response Model
```python
class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: str
    error_type: str
```

### HTTP Status Codes
- 400: Invalid parameters (temperature, model)
- 401: Authentication errors
- 404: Model/resource not found
- 429: Rate limit exceeded
- 500: Internal server errors

### Error Type Detection
The API automatically detects error types based on error message content:
- Authentication errors → 401
- Rate limits → 429
- Not found → 404
- Invalid model → 400
- Temperature/parameter issues → 400
- Everything else → 500

## Testing Error Scenarios

### Test Temperature Error (o1 models)
1. Select provider: OpenAI
2. Select model: o1-mini
3. Set temperature to 0.5 (slider)
4. Send a message
5. Should see: "❌ Temperature Not Supported" (but this is now prevented by frontend)

### Test Authentication Error
1. Rename .env file temporarily
2. Restart server
3. Try to send a message
4. Should see: "🔑 Authentication Error"

### Test Connection Error
1. Stop the FastAPI server
2. Try to send a message from GUI
3. Should see: "🌐 Connection Error"

## Prevention Measures

The system now has multiple layers of protection:

1. **Frontend Detection**: Temperature slider is disabled for reasoning models
2. **API Layer Detection**: API validates and overrides temperature before sending to provider
3. **Provider Layer Detection**: Each provider checks model type before including temperature parameter
4. **Error Reporting**: If something slips through, users get clear, actionable error messages

This multi-layered approach ensures maximum reliability and user experience.
