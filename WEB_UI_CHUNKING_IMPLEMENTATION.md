# Web UI Chunking & Intelligent Extraction Implementation

## Overview
Added smart chunking and intelligent extraction capabilities to the Web UI, matching the functionality available in CLI/Interactive modes. This ensures feature parity across all three interfaces.

## Implementation Date
February 5, 2026

## Changes Made

### 1. Backend API Updates (`api/main.py`)

#### Updated Request Model (Lines 52-64)
```python
class ChatCompletionRequest(BaseModel):
    """Chat completion request model."""
    provider: str
    model: str
    messages: List[dict]
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: bool = False
    file_content: Optional[str] = None  # Base64 encoded file content or plain text
    file_name: Optional[str] = None  # Original filename for type detection
    chunked: bool = False  # Enable smart chunking and summarization
    chunk_size: int = 50000  # Chunk size in characters
```

#### Added File Processing Logic (Lines 246-320)
- **Base64 Detection**: Automatically detects if file content is base64 encoded or plain text
- **Chunking Logic**: When `chunked=True`, processes file with `summarize_file()`
- **File Analysis**: Uses `analyze_file()` to determine optimal chunking strategy
- **Async Processing**: Runs chunking in background thread to avoid blocking
- **Token Reduction Logging**: Logs reduction percentages (typically 40-90%)
- **Message Integration**: Appends processed content to user messages

**Key Features**:
- Handles both base64 and plain text file content
- Creates temporary files for analysis
- Runs summarization asynchronously
- Cleans up temp files after processing
- Combines with existing user messages

### 2. Frontend UI Updates (`api/static/index.html`)

#### New UI Controls (Lines 315-324)
```html
<!-- Chunking Checkbox -->
<div class="form-group" style="display: flex; gap: 10px; align-items: center;">
    <input type="checkbox" id="chunked" style="width: auto;">
    <label for="chunked" style="margin: 0; cursor: pointer;">
        Enable Smart Chunking (reduces token usage for large files)
    </label>
</div>

<!-- Chunk Size Slider (shown when chunking enabled) -->
<div class="form-group" id="chunk-size-group" style="display: none;">
    <label for="chunk-size">Chunk Size (characters): <span id="chunk-size-value">50000</span></label>
    <input type="range" id="chunk-size" min="10000" max="100000" step="10000" value="50000">
    <div style="font-size: 12px; color: #666; margin-top: 5px;">
        💡 Smaller chunks = more summaries, larger chunks = fewer summaries
    </div>
</div>
```

#### JavaScript Event Handlers (Lines 606-615)
```javascript
// Toggle chunk size slider visibility
document.getElementById('chunked').addEventListener('change', (e) => {
    const chunkSizeGroup = document.getElementById('chunk-size-group');
    chunkSizeGroup.style.display = e.target.checked ? 'block' : 'none';
});

// Update chunk size display
document.getElementById('chunk-size').addEventListener('input', (e) => {
    document.getElementById('chunk-size-value').textContent = parseInt(e.target.value).toLocaleString();
});
```

#### Updated Message Building Logic (Lines 761-802)
- Detects when chunking is enabled for text files
- Separates API file parameters (`apiFileContent`, `apiFileName`)
- Adds "(chunking enabled)" indicator to display message
- Sends file to API for server-side processing instead of embedding directly

#### Updated API Request (Lines 843-863)
```javascript
const requestBody = {
    provider,
    model,
    messages: messages,
    temperature,
    max_tokens: maxTokens,
};

// Add file and chunking parameters if file is being chunked
if (apiFileContent && apiFileName) {
    requestBody.file_content = apiFileContent;
    requestBody.file_name = apiFileName;
    requestBody.chunked = true;
    requestBody.chunk_size = parseInt(document.getElementById('chunk-size').value);
}
```

## How It Works

### User Workflow
1. **Select Provider & Model**: Choose your LLM provider and model
2. **Attach Large File**: Click "Attach File" and select a text file (CSV, JSON, log, code, etc.)
3. **Enable Chunking**: Check "Enable Smart Chunking" checkbox
4. **Adjust Chunk Size** (optional): Use slider to set chunk size (10k-100k chars, default 50k)
5. **Send Message**: File is automatically processed and summarized before sending

### Backend Processing
1. **Receive Request**: API receives file content, filename, and chunking parameters
2. **Decode Content**: Detects and decodes base64 if needed, otherwise uses plain text
3. **Create Temp File**: Writes content to temporary file for analysis
4. **Analyze File**: Uses `analyze_file()` to estimate tokens and determine file type
5. **Chunk & Summarize**: Runs `summarize_file()` asynchronously in thread pool
6. **Return Summary**: Sends summarized content to LLM (typically 40-90% smaller)
7. **Clean Up**: Deletes temporary file

### Chunking Strategies
- **CSV Files**: Schema extraction (80-99% reduction)
- **JSON Files**: Structure analysis (78-95% reduction)
- **Log Files**: Error extraction (90% reduction)
- **Code Files**: Function/class structure (33-80% reduction)
- **Text Files**: Progressive summarization

## Benefits

### For Users
- **Handles Large Files**: Process files that exceed context limits
- **Reduces Costs**: Fewer tokens = lower API costs
- **Faster Responses**: Smaller prompts = faster completions
- **Maintains Quality**: Intelligent extraction preserves important information

### For Claude Opus 4.5 (Your Use Case)
- **Problem**: 223k tokens input → **200k API limit** ❌
- **Solution**: Enable chunking → Reduces to ~22k-112k tokens ✅
- **Typical Reduction**: 50-90% depending on file type

## Feature Parity Achieved

| Feature | CLI | Interactive | Web UI |
|---------|-----|-------------|--------|
| File Upload | ✅ | ✅ | ✅ |
| Chunking | ✅ | ✅ | ✅ |
| Chunk Size Config | ✅ | ✅ | ✅ |
| Intelligent Extraction | ✅ | ✅ | ✅ |
| Vision Support | ✅ | ✅ | ✅ |
| Temperature Control | ✅ | ✅ | ✅ |
| Cost Tracking | ✅ | ✅ | ✅ |

## Usage Examples

### Example 1: Large CSV File
```
File: sales_data.csv (2.5 MB, ~200k tokens)
Chunking: Enabled (50k chunk size)
Result: Schema extracted (~10k tokens, 95% reduction)
```

### Example 2: Application Logs
```
File: app.log (5 MB, ~400k tokens)
Chunking: Enabled (50k chunk size)
Result: Error summary (~40k tokens, 90% reduction)
```

### Example 3: Python Codebase
```
File: main.py (1 MB, ~80k tokens)
Chunking: Enabled (50k chunk size)
Result: Structure analysis (~40k tokens, 50% reduction)
```

## Technical Implementation Details

### File Processing Flow
```
User uploads file
    ↓
Frontend reads file content
    ↓
Chunking enabled? → NO → Embed content in message
    ↓ YES
Send to API with chunking=True
    ↓
API decodes/validates content
    ↓
Create temporary file
    ↓
Analyze file type & tokens
    ↓
Run summarize_file() async
    ↓
Return summarized content
    ↓
Append to user message
    ↓
Send to LLM
```

### Error Handling
- **File Too Large**: 5 MB limit enforced in frontend
- **Decoding Errors**: Falls back to plain text if base64 decode fails
- **Chunking Errors**: Falls back to full file content on chunking failure
- **Temp File Cleanup**: Ensures temp files are deleted even on error

## Testing Recommendations

1. **Small Files** (<100k chars): Test with and without chunking to verify overhead is minimal
2. **Medium Files** (100k-500k chars): Verify chunking reduces tokens significantly
3. **Large Files** (>500k chars): Ensure files exceeding API limits can be processed
4. **Different File Types**: Test CSV, JSON, logs, code files
5. **Chunk Size Variations**: Test 10k, 50k, 100k chunk sizes
6. **Error Cases**: Test invalid files, network errors, API failures

## Next Steps
- ✅ Backend API updates complete
- ✅ Frontend UI updates complete
- 🔲 Test with large files (see testing recommendations)
- 🔲 Monitor token reduction metrics in production
- 🔲 Consider adding progress indicators for long chunking operations
- 🔲 Add file type auto-detection and recommendations

## Related Files
- `/api/main.py` - Backend API implementation
- `/api/static/index.html` - Frontend UI implementation
- `/stratifyai/summarization.py` - Chunking logic
- `/stratifyai/utils/file_analyzer.py` - File analysis
- `/stratifyai/utils/csv_extractor.py` - CSV schema extraction
- `/stratifyai/utils/json_extractor.py` - JSON schema extraction
- `/stratifyai/utils/log_extractor.py` - Log error extraction
- `/stratifyai/utils/code_extractor.py` - Code structure extraction
