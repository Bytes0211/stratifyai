# Temperature Functionality Implementation - Interactive Mode

## Summary
Implemented temperature prompting in interactive mode to match chat mode behavior. Users are now prompted for temperature only for models with dynamic temperature values. Reasoning models with fixed temperature (like o1, o3-mini, deepseek-reasoner) automatically use their fixed value without prompting.

## Changes Made

### 1. Initial Model Selection (Lines 1251-1286)
**Location**: `cli/stratifyai_cli.py` after model selection, before client initialization

**Logic**:
```python
# Check if model has fixed temperature
model_info = MODEL_CATALOG.get(provider, {}).get(model, {})
fixed_temp = model_info.get("fixed_temperature")

if fixed_temp is not None:
    temperature = fixed_temp
    console.print(f"\n[dim]Using fixed temperature: {fixed_temp} for this model[/dim]")
else:
    # Prompt user for temperature (0.0-2.0, default 0.7)
    # Includes retry loop for validation
```

**Behavior**:
- **Fixed temperature models**: Display message, skip prompt, use fixed value
- **Dynamic temperature models**: Prompt user with default 0.7, validate range (0.0-2.0)

### 2. Model Switching via /provider Command (Lines 1626-1661)
**Location**: `cli/stratifyai_cli.py` in `/provider` command handler after model selection

**Logic**: Identical to initial selection - checks for fixed_temperature and prompts only for dynamic models

**Behavior**: Consistent temperature handling when switching providers/models mid-conversation

### 3. Vision Model Reselection Workflow (Lines 869-1015)
**Location**: `cli/stratifyai_cli.py` in `load_file_content()` helper function

**Changes**:
- Added `nonlocal temperature` declaration at function top (line 870)
- Added temperature prompting when switching to vision model (lines 972-1007)
- Moved `nonlocal` declarations before any variable use to fix syntax error

**Behavior**: When user uploads image with non-vision model and switches to vision model, they're prompted for temperature before loading image

### 4. ChatRequest Update (Line 1759)
**Location**: `cli/stratifyai_cli.py` in conversation loop

**Change**: `ChatRequest(model=model, messages=messages, temperature=temperature)`

**Behavior**: All chat completions now use the configured temperature value

## Model Categories

### Fixed Temperature Models (No Prompt)
These models automatically use `fixed_temperature: 1.0` from config:
- **OpenAI**: o1, o1-mini, o3-mini, o1-preview, o1-2024-12-17, o1-mini-2024-09-12, gpt-5
- **DeepSeek**: deepseek-reasoner

### Dynamic Temperature Models (Prompt User)
All other models prompt for temperature:
- **OpenAI**: gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-4, gpt-3.5-turbo, gpt-5-mini, gpt-5-nano, gpt-4.1, gpt-4.1-mini
- **Anthropic**: All Claude models (3.5, 3.7, 4, 4.5)
- **Google**: gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite
- **DeepSeek**: deepseek-chat
- **Groq**: All Llama models
- **Grok**: grok-beta
- **OpenRouter**: All models
- **Ollama**: All models
- **Bedrock**: All models

## Temperature Validation
- **Range**: 0.0 to 2.0 (matches OpenAI API range)
- **Default**: 0.7
- **Retry**: 3 attempts with user-friendly error messages
- **Fallback**: If user fails validation, defaults to 0.7

## User Experience

### Initial Setup (Dynamic Temperature)
```
Select Provider
  1. openai
  2. anthropic
  ...

Choose provider: 1

✓ Validated 15 models (245ms)

Available openai models:
  ── Current Models ──
  1. GPT-4o - Best quality, vision/tools support
  2. GPT-4o Mini - Fast, cost-effective

Select model: 1

Temperature (0.0-2.0, default 0.7): 0.8

File Attachment (Optional)
...
```

### Initial Setup (Fixed Temperature)
```
Select Provider
...
Select model: 3  # o1

Using fixed temperature: 1.0 for this model

File Attachment (Optional)
...
```

### Model Switching via /provider
```
/provider

Switch Provider and Model
Your conversation history will be preserved

Available providers:
  1. openai (current)
  2. anthropic
  ...

Select provider: 2

✓ Validated 12 models (198ms)

Available anthropic models:
  1. Claude Sonnet 4.5 - Best reasoning, vision
  ...

Select model: 1

Temperature (0.0-2.0, default 0.7): 0.7

✓ Switched to: anthropic | claude-sonnet-4-5 | Context: 200,000 tokens
Conversation history preserved
```

### Vision Model Reselection
```
✗ Vision not supported: gpt-4-turbo cannot process image files
⚠️ This model cannot process images. Switching to vision-capable model...

Enter 1 to select a vision-capable model or 2 to continue without image: 1

✓ Validated 15 models (234ms)

Vision-capable models for openai:
(Filtered for image file support)
  1. GPT-4o - Best quality, vision/tools support
  2. GPT-4o Mini - Fast, cost-effective

Select vision model: 1

Temperature (0.0-2.0, default 0.7): 0.9

✓ Switched to: gpt-4o | Context: 128,000 tokens

✓ Loaded image.png (245.3 KB, image)
```

## Consistency with Chat Mode
Temperature handling in interactive mode now matches chat mode exactly:
1. Same temperature check logic
2. Same prompting behavior (fixed vs dynamic)
3. Same validation and retry mechanism
4. Same default value (0.7)
5. Same range (0.0-2.0)

## Testing
To test the implementation:
1. Start interactive mode: `stratifyai interactive`
2. Select a reasoning model (o1, o3-mini, deepseek-reasoner) → Should display fixed temperature message
3. Select a standard model (gpt-4o, claude-sonnet) → Should prompt for temperature
4. Use `/provider` to switch models → Should prompt for temperature again
5. Upload image with non-vision model and switch → Should prompt for temperature before loading image

## Files Modified
- `cli/stratifyai_cli.py` (5 locations):
  - Lines 1251-1286: Initial model selection temperature handling (interactive mode)
  - Lines 1626-1661: /provider command temperature handling (interactive mode)
  - Lines 869-1015: Vision reselection temperature handling (interactive mode)
  - Line 1759: ChatRequest temperature parameter (interactive mode)
  - Lines 444-452: Message prompting for image files (chat mode fix)

## Additional Fix: Chat Mode Message Prompting
Fixed an issue where chat mode wouldn't prompt for a message after vision model reselection. The problem was that the message prompt condition checked `if not message and not file_content`, which would skip prompting when an image file was loaded (since `file_content` exists).

**Solution**: Changed the condition to always prompt for image files, since users need to provide instructions for what to do with the image:
```python
is_image_file = file and file.suffix.lower() in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'} if file else False

if not message:
    if is_image_file or not file_content:
        console.print("\n[bold cyan]Enter your message:[/bold cyan]")
        message = Prompt.ask("Message")
```

This ensures that:
- Image files: Always prompt for message (user provides instructions)
- Text files: Only prompt if no file content
- After vision error and model reselection: User is prompted for their message

## Related Configuration
Temperature behavior is controlled by `fixed_temperature` field in `stratifyai/config.py`:
- Present: Model has fixed temperature (no prompt)
- Absent: Model has dynamic temperature (prompt user)
