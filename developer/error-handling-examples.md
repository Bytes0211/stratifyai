# Error Handling Examples

## Overview

StratifyAI CLI now includes robust error handling with retry logic for all interactive prompts. Users get **3 attempts** to provide valid input before the system takes a default action.

## Provider Selection Errors

### Example 1: Alphabetical Input Instead of Number

**User enters letters instead of number:**

```
Select Provider
  1. openai
  2. anthropic
  3. google
  4. deepseek
  5. groq
  6. grok
  7. ollama
  8. openrouter

Choose provider [1]: openai
✗ Invalid input. Please enter a number, not letters (e.g., '1' not 'openai')
Try again...

Choose provider [1]: anthropic
✗ Invalid input. Please enter a number, not letters (e.g., '1' not 'openai')
Try again...

Choose provider [1]: google
✗ Invalid input. Please enter a number, not letters (e.g., '1' not 'openai')
Too many invalid attempts. Using default: openai
```

**Result**: System uses default provider (OpenAI) after 3 failed attempts.

### Example 2: Number Out of Range

**User enters number outside valid range:**

```
Choose provider [1]: 10
✗ Invalid number. Please enter a number between 1 and 8
Try again...

Choose provider [1]: 0
✗ Invalid number. Please enter a number between 1 and 8
Try again...

Choose provider [1]: 2
```

**Result**: System accepts valid input on 3rd attempt (Anthropic).

### Example 3: Empty Input Uses Default

**User just presses Enter:**

```
Choose provider [1]: 
```

**Result**: System uses default value (1 = OpenAI) immediately.

## Model Selection Errors

### Example 1: Typing Model Name

**User types model name instead of number:**

```
Available models for openai:
  1. gpt-4o
  2. gpt-4o-mini
  3. o1
  4. o1-mini
  5. o3-mini

Select model: gpt-4o
✗ Invalid input. Please enter a number, not the model name (e.g., '2' not 'gpt-4o')
Try again...

Select model: 2
```

**Result**: System accepts valid input on 2nd attempt (gpt-4o-mini).

### Example 2: Number Out of Range - Exits After 3 Attempts

**User repeatedly enters invalid numbers:**

```
Select model: 10
✗ Invalid number. Please enter a number between 1 and 5
Try again...

Select model: 0
✗ Invalid number. Please enter a number between 1 and 5
Try again...

Select model: -1
✗ Invalid number. Please enter a number between 1 and 5
Too many invalid attempts. Exiting.
```

**Result**: System exits because model selection is critical (no safe default).

### Example 3: Mixed Invalid Input

**User makes different types of errors:**

```
Select model: gpt-4
✗ Invalid input. Please enter a number, not the model name (e.g., '2' not 'gpt-4o')
Try again...

Select model: 100
✗ Invalid number. Please enter a number between 1 and 5
Try again...

Select model: 1
```

**Result**: System accepts valid input on 3rd attempt (gpt-4o).

## Temperature Selection Errors

### Example 1: Alphabetical Input

**User enters text instead of number:**

```
Temperature (0.0-2.0, default 0.7) [0.7]: high
✗ Invalid input. Please enter a number (e.g., '0.7' not 'high')
Try again...

Temperature (0.0-2.0, default 0.7) [0.7]: medium
✗ Invalid input. Please enter a number (e.g., '0.7' not 'medium')
Try again...

Temperature (0.0-2.0, default 0.7) [0.7]: low
✗ Invalid input. Please enter a number (e.g., '0.7' not 'low')
Too many invalid attempts. Using default: 0.7
```

**Result**: System uses default temperature (0.7) after 3 failed attempts.

### Example 2: Out of Range Number

**User enters valid number but outside range:**

```
Temperature (0.0-2.0, default 0.7) [0.7]: 3.0
✗ Out of range. Temperature must be between 0.0 and 2.0
Try again...

Temperature (0.0-2.0, default 0.7) [0.7]: -1.0
✗ Out of range. Temperature must be between 0.0 and 2.0
Try again...

Temperature (0.0-2.0, default 0.7) [0.7]: 1.2
```

**Result**: System accepts valid temperature (1.2) on 3rd attempt.

### Example 3: Empty Input Uses Default

**User presses Enter without input:**

```
Temperature (0.0-2.0, default 0.7) [0.7]: 
```

**Result**: System uses default (0.7) immediately.

## Complete Interactive Session with Errors

**Full example showing error recovery:**

```bash
$ python -m cli.stratifyai_cli chat

Select Provider
  1. openai
  2. anthropic
  3. google
  4. deepseek
  5. groq
  6. grok
  7. ollama
  8. openrouter

Choose provider [1]: google
✗ Invalid input. Please enter a number, not letters (e.g., '1' not 'openai')
Try again...

Choose provider [1]: 3

Available models for google:
  1. gemini-2.0-flash-exp
  2. gemini-2.0-flash-thinking-exp-1219
  3. gemini-2.5-flash-lite
  4. gemini-exp-1206

Select model: gemini-flash
✗ Invalid input. Please enter a number, not the model name (e.g., '2' not 'gpt-4o')
Try again...

Select model: 1

Temperature (0.0-2.0, default 0.7) [0.7]: warm
✗ Invalid input. Please enter a number (e.g., '0.7' not 'warm')
Try again...

Temperature (0.0-2.0, default 0.7) [0.7]: 0.8

File Attachment (Optional)
Attach a file to include its content in your message
Max file size: 5 MB | Leave blank to skip

File path (or press Enter to skip): 

Enter your message:
Message: What is AI?

Provider: google | Model: gemini-2.0-flash-exp
Context: 1,000,000 tokens | Tokens: 156 | Cost: $0.000012

[AI response...]
```

**Result**: User successfully completes session despite multiple input errors.

## Error Handling Philosophy

### 1. **Forgiving for Defaults**
- Provider: Uses OpenAI (safe, widely available)
- Temperature: Uses 0.7 (balanced default)
- **Why**: These have reasonable defaults

### 2. **Strict for Critical Choices**
- Model: Exits after 3 attempts
- **Why**: No safe default—model choice is essential to user intent

### 3. **Helpful Error Messages**
- ✗ Clear indicator of error
- Specific explanation of what went wrong
- Example of correct input format
- "Try again..." encouragement

### 4. **Progressive Disclosure**
- Attempt 1-2: "Try again..."
- Attempt 3: Final action (default or exit)
- **Why**: Reduces cognitive load, clear escalation

## Benefits for Non-Technical Users

### Before (Harsh)
```
Select model: gpt-4
Invalid input. Please enter a number.
[System exits]
```

### After (Forgiving)
```
Select model: gpt-4
✗ Invalid input. Please enter a number, not the model name (e.g., '2' not 'gpt-4o')
Try again...

Select model: 2
```

**Impact:**
- Reduces frustration
- Prevents accidental exits
- Teaches correct format
- Allows error recovery
- Builds user confidence

## Testing Error Handling

### Manual Testing Scenarios

1. **Provider Selection**
   - Enter: `openai` → Expect retry
   - Enter: `anthropic` → Expect retry
   - Enter: `google` → Expect default (openai)

2. **Model Selection**
   - Enter: `gpt-4` → Expect retry
   - Enter: `0` → Expect retry
   - Enter: `100` → Expect exit

3. **Temperature**
   - Enter: `high` → Expect retry
   - Enter: `5.0` → Expect retry
   - Enter: `-1.0` → Expect default (0.7)

4. **Mixed Errors**
   - Combine different error types
   - Verify graceful recovery
   - Check final state is correct

## Implementation Details

### Retry Logic
```python
max_attempts = 3
for attempt in range(max_attempts):
    user_input = Prompt.ask("...")
    
    try:
        # Validate input
        if valid:
            break  # Success!
        else:
            # Show error, allow retry
            if attempt < max_attempts - 1:
                console.print("Try again...")
            else:
                # Final attempt: take action
                console.print("Using default...")
    except ValueError:
        # Handle parse errors
        console.print("Invalid input...")
```

### Error Message Format
- **Symbol**: ✗ (red) for errors
- **Explanation**: Clear reason
- **Example**: Show correct format
- **Action**: What happens next

### Defaults Strategy
- **Provider**: `openai` (most compatible)
- **Model**: No default (too variable)
- **Temperature**: `0.7` (balanced)

## Edge Cases Handled

1. **Empty input**: Uses default value
2. **Whitespace**: Trimmed and validated
3. **Special characters**: Caught by ValueError
4. **Very large numbers**: Range validation
5. **Negative numbers**: Range validation
6. **Decimal vs integer**: float() handles both
7. **Multiple retries**: Counted and limited

## Future Enhancements

Potential improvements:
- Fuzzy matching for model names
- Auto-correct common typos
- Suggest most similar option
- Remember user preferences
- Configurable retry limit
