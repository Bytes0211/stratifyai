# Conversation Flow Fix

## Problem
When using `stratumai chat`, after the LLM responded with clarification questions, the CLI prompted to "Save response as markdown?" with a Y/N input. This prevented users from replying to continue the conversation.

## Root Cause
The `chat` command flow was:
1. Display response
2. Immediately ask "Save as markdown?" 
3. Only then ask "Send another message?"
4. **No conversation history maintained** - follow-ups lost all context

## Solution
Modified the `chat` command to:
1. Display response
2. Present 4 clear options:
   - [1] Continue conversation (default)
   - [2] Save & continue
   - [3] Save & exit
   - [4] Exit
3. **Maintain conversation history** across follow-up messages
4. Support both follow-up questions and saving

## Changes Made

### 1. Added conversation history parameter
```python
_conversation_history: Optional[List[Message]] = None,  # Internal parameter for recursion
```

### 2. Build messages with history
```python
# Build messages - use conversation history if this is a follow-up
if _conversation_history is None:
    messages = []
    if system:
        messages.append(Message(role="system", content=system))
else:
    messages = _conversation_history.copy()
```

### 3. Updated post-response flow
```python
# Add assistant response to history for multi-turn conversation
messages.append(Message(role="assistant", content=response_content))

# Ask what to do next
console.print("\n[dim]Options: [1] Continue conversation  [2] Save & continue  [3] Save & exit  [4] Exit[/dim]")
next_action = Prompt.ask("What would you like to do?", choices=["1", "2", "3", "4"], default="1")
```

### 4. Save full conversation history
When saving to markdown, the entire conversation is now saved:
```python
# Write full conversation history
for msg in messages:
    if msg.role == "user":
        f.write(f"**You:** {msg.content}\n\n")
    elif msg.role == "assistant":
        f.write(f"**Assistant:** {msg.content}\n\n")
```

### 5. Pass history to recursive call
```python
# Recursive call with conversation history
chat(None, provider, model, temperature, max_tokens, stream, None, None, False, messages)
```

## Testing

### Before Fix
```
Message: provide a population racial breakdown of texas.

[Response with clarification questions]

Save response as markdown? [y/n] (n): yes US state Texas 2020 Census.
Please enter Y or N
```
❌ User tried to reply but was stuck in Y/N prompt

### After Fix
```
Message: provide a population racial breakdown of texas.

[Response with clarification questions]

Options: [1] Continue conversation  [2] Save & continue  [3] Save & exit  [4] Exit
What would you like to do? [1/2/3/4] (1): 1

Message: yes US state Texas 2020 Census.

[Response with actual data, maintaining conversation context]
```
✅ User can reply naturally and conversation context is maintained

## Recommendation for Users

For extended multi-turn conversations, use `stratumai interactive` instead:
```bash
python -m cli.stratumai_cli interactive -p openai -m gpt-4o-mini
```

The `interactive` command provides a better UX for back-and-forth conversations without prompting for saves after each message.
