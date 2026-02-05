# Vision Error Model Reselection Feature

## Date
February 5, 2026

## Feature
When a user tries to upload an image with a non-vision model, instead of exiting with an error, the system now loops back to model selection or provides guidance to select a vision-capable model.

---

## Implementation

### Chat Mode (`stratifyai chat`)
**File:** `cli/stratifyai_cli.py`

#### Pre-emptive Filtering (Lines 177-226)
When an image file is provided at the start:
1. Detects if file is an image based on extension
2. **Automatically filters** model list to show only vision-capable models
3. Displays "(Filtered for image file support)" message
4. Adds (vision) label to vision models when no image provided

**Example Output:**
```bash
$ stratifyai chat --file data/hawk.jpg

Select Provider
  1. openai
  [...]

Choose provider: 1
✓ Validated 5 models

Vision-capable models for openai:
(Filtered for image file support)
  1. gpt-4o
  2. gpt-4o-mini

Select model: 1
```

#### Reactive Reselection (Lines 360-376)
If vision check fails during file upload:
1. Shows friendly error message
2. Displays "Returning to model selection..."
3. Recursively calls `chat()` command with provider preserved
4. User gets fresh model selection with vision models

**Example Output:**
```bash
File path: data/hawk.jpg

✗ Vision not supported: gpt-4-turbo cannot process image files
⚠️ This model cannot process images. Please select a vision-capable model.

Returning to model selection...

Vision-capable models for openai:
(Filtered for image file support)
  1. gpt-4o
  2. gpt-4o-mini

Select model:
```

---

### Interactive Mode (`stratifyai interactive`)
**File:** `cli/stratifyai_cli.py` (Lines 877-892)

#### Guided Model Switch
When user tries to load an image during session:
1. Shows friendly error message
2. Offers choice: "1 to select vision model" or "2 to continue without image"
3. Provides guidance to use `/provider` command
4. User remains in session (doesn't exit)

**Example Output:**
```bash
You: /file data/hawk.jpg

✗ Vision not supported: gpt-4-turbo cannot process image files
⚠️ This model cannot process images. Switching to vision-capable model...

Enter 1 to select a vision-capable model or 2 to continue without image (1): 1

Use the /provider command to switch to a vision-capable model
Example: /provider

You: /provider
```

Then the `/provider` command allows switching provider/model.

---

## User Experience

### Before
```bash
File path: data/hawk.jpg
✗ Vision not supported: gpt-4-turbo cannot process image files
⚠️ Please select a vision-capable model
[EXIT]
```
**Problem:** User had to restart command entirely

### After (Chat Mode)
```bash
File path: data/hawk.jpg
✗ Vision not supported: gpt-4-turbo cannot process image files
⚠️ This model cannot process images. Please select a vision-capable model.

Returning to model selection...

Vision-capable models for openai:
(Filtered for image file support)
  1. gpt-4o
  2. gpt-4o-mini

Select model: 1
[CONTINUES]
```
**Benefit:** Seamless recovery without restarting

### After (Interactive Mode)
```bash
You: /file data/hawk.jpg
✗ Vision not supported: gpt-4-turbo cannot process image files
⚠️ This model cannot process images. Switching to vision-capable model...

Enter 1 to select vision model or 2 to continue without image: 1

Use /provider command to switch model

You: /provider
[SWITCHES MODEL, STAYS IN SESSION]
```
**Benefit:** User guidance without exiting session

---

## Technical Details

### Chat Mode Enhancements

#### 1. Pre-emptive Filtering
```python
# Detect if image file (line 178)
need_vision_model = file and file.suffix.lower() in {'.jpg', '.jpeg', '.png', ...}

# Filter models (lines 205-210)
if need_vision_model:
    vision_models = [m for m in available_models 
                     if model_metadata.get(m, {}).get("supports_vision", False)]
    if vision_models:
        console.print("Vision-capable models for {provider}:")
        available_models = vision_models
```

#### 2. Model Labels
```python
# Add (vision) label (lines 220-226)
if supports_vision and not need_vision_model:
    label += " [magenta](vision)[/magenta]"
```

#### 3. Recursive Reselection
```python
# On vision error (lines 365-376)
console.print("Returning to model selection...")
chat(provider=provider, model=None, message=message, ...)
return
```

### Interactive Mode Enhancements

#### User Choice on Error
```python
# On vision error (lines 882-891)
choice = Prompt.ask(
    "Enter 1 to select vision model or 2 to continue without image",
    choices=["1", "2"],
    default="1"
)

if choice == "1":
    console.print("Use /provider command to switch model")
```

---

## Edge Cases Handled

### 1. Provider with No Vision Models
```bash
✓ Validated 4 models

⚠ No vision-capable models available for deepseek
Please select a different provider or remove the image file
[EXIT]
```

### 2. Image Added After Model Selection (Chat)
Triggers recursive reselection with pre-filtered list

### 3. Image Added During Session (Interactive)
Provides guidance to use `/provider` command

---

## Benefits

1. **No More Restarts:** Users don't have to exit and restart the command
2. **Smart Filtering:** Vision models automatically shown when image detected
3. **Clear Guidance:** Tells users exactly what to do
4. **Maintains Context:** Interactive mode stays in session
5. **Better UX:** Seamless error recovery vs hard exit

---

## Files Modified

1. `cli/stratifyai_cli.py`
   - Lines 177-179: Pre-emptive vision detection
   - Lines 204-216: Vision model filtering
   - Lines 220-226: Vision labels
   - Lines 360-376: Recursive reselection (chat mode)
   - Lines 877-892: Guided switching (interactive mode)

**Total Changes:** ~50 lines across 5 locations

---

## Testing

### Test Scenario 1: Image with Non-Vision Provider
```bash
$ stratifyai chat --provider deepseek --file data/hawk.jpg
⚠ No vision-capable models available for deepseek
```
**Result:** Clear message to choose different provider

### Test Scenario 2: Image Selected After Model
```bash
$ stratifyai chat --provider openai --model gpt-4-turbo
File path: data/hawk.jpg
✗ Vision not supported...
Returning to model selection...
[SHOWS FILTERED LIST]
```
**Result:** Automatic reselection with vision models

### Test Scenario 3: Interactive Session Image Load
```bash
You: /file data/hawk.jpg
✗ Vision not supported...
Enter 1 to select vision model or 2 to continue: 1
Use /provider command...
```
**Result:** Guided to model switch command

---

## Summary

**Problem:** Users hit dead-end errors when trying images with non-vision models  
**Solution:** Automatic reselection (chat) and guided switching (interactive)  
**Result:** Seamless error recovery without losing context or restarting  

Users now have a smooth experience when selecting models for vision tasks!
