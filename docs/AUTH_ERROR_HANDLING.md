# Enhanced Authentication Error Handling

## Overview
StratifyAI CLI now provides enhanced, user-friendly error messages when API authentication fails. Instead of a generic error, users receive clear, actionable instructions specific to each provider.

## Implementation Date
February 3, 2026

## What Changed

### Before
```
Error: Authentication failed for grok. Check API key.
```

### After
```
✗ Authentication Failed
Provider: grok
Issue: API key is missing or invalid

How to fix:
  1. Set the environment variable: GROK_API_KEY
     export GROK_API_KEY="your-api-key-here"

  2. Or add to your .env file in the project root:
     GROK_API_KEY=your-api-key-here

Get your API key from: https://console.x.ai/
```

## Features

### 1. Provider-Specific Instructions
Each provider gets customized guidance with:
- Correct environment variable name (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`)
- Direct link to get API keys
- Provider-specific setup instructions

### 2. Multiple Resolution Paths
Users are shown two ways to fix the issue:
1. Export environment variable in terminal
2. Add to `.env` file in project root

### 3. Rich Formatting
- Color-coded output (red for errors, cyan for instructions, green for highlights)
- Clear visual hierarchy with ✗ symbol
- Consistent formatting across all providers

### 4. Interactive Mode Support
In `stratifyai interactive` mode:
- Authentication errors don't crash the session
- Users can continue the conversation after fixing the API key
- History is preserved (failed message is removed)

## Supported Providers

| Provider | Environment Variable | API Key URL |
|----------|---------------------|-------------|
| OpenAI | `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| Anthropic | `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |
| Google | `GOOGLE_API_KEY` | https://aistudio.google.com/app/apikey |
| DeepSeek | `DEEPSEEK_API_KEY` | https://platform.deepseek.com/api_keys |
| Groq | `GROQ_API_KEY` | https://console.groq.com/keys |
| Grok (X.AI) | `GROK_API_KEY` | https://console.x.ai/ |
| OpenRouter | `OPENROUTER_API_KEY` | https://openrouter.ai/keys |
| Ollama | `OLLAMA_API_KEY` | Local - run `ollama serve` |

## Technical Details

### Modified Files
1. **cli/stratifyai_cli.py**
   - Added `AuthenticationError` import
   - Added `PROVIDER_ENV_VARS` import from config
   - Added specific exception handlers in `_chat_impl()` and `interactive()` commands
   - Three handler locations:
     - Chat command (single-turn)
     - Interactive mode (per-message)
     - Interactive mode (session-level)

2. **tests/test_cli_auth_error.py** (NEW)
   - Comprehensive test suite for auth error handling
   - Tests for all 8 providers
   - Validates error message content and formatting
   - 8 passing tests

### Code Structure
```python
except AuthenticationError as e:
    # Display error header
    console.print(f"\n[red]✗ Authentication Failed[/red]")
    console.print(f"[yellow]Provider:[/yellow] {e.provider}")
    console.print(f"[yellow]Issue:[/yellow] API key is missing or invalid\n")
    
    # Get environment variable name
    env_var = PROVIDER_ENV_VARS.get(e.provider, f"{e.provider.upper()}_API_KEY")
    
    # Show fix instructions
    console.print("[bold cyan]How to fix:[/bold cyan]")
    console.print(f"  1. Set the environment variable: [green]{env_var}[/green]")
    console.print(f"     export {env_var}=\"your-api-key-here\"")
    console.print(f"\n  2. Or add to your [green].env[/green] file in the project root:")
    console.print(f"     {env_var}=your-api-key-here\n")
    
    # Provider-specific link
    if e.provider == "grok":
        console.print("[dim]Get your API key from: https://console.x.ai/[/dim]")
    # ... (other providers)
```

## Testing

### Unit Tests
Run the auth error tests:
```bash
pytest tests/test_cli_auth_error.py -v
```

### Manual Testing
Test with a missing API key:
```bash
# Remove or unset the API key
unset GROK_API_KEY

# Try to use the CLI
uv run stratifyai chat "test" --provider grok --model grok-beta

# Expected: Clear error message with instructions
```

### Test Results
```
tests/test_cli_auth_error.py::TestAuthenticationErrorHandling::test_chat_displays_auth_error_with_instructions PASSED
tests/test_cli_auth_error.py::TestAuthenticationErrorHandling::test_chat_openai_auth_error PASSED
tests/test_cli_auth_error.py::TestAuthenticationErrorHandling::test_chat_anthropic_auth_error PASSED
tests/test_cli_auth_error.py::TestAuthenticationErrorHandling::test_chat_google_auth_error PASSED
tests/test_cli_auth_error.py::TestAuthenticationErrorHandling::test_chat_deepseek_auth_error PASSED
tests/test_cli_auth_error.py::TestAuthenticationErrorHandling::test_chat_groq_auth_error PASSED
tests/test_cli_auth_error.py::TestAuthenticationErrorHandling::test_chat_openrouter_auth_error PASSED
tests/test_cli_auth_error.py::TestAuthenticationErrorHandling::test_chat_ollama_auth_error PASSED

8 passed in 0.41s
```

All existing CLI tests (42 total) continue to pass.

## Benefits

1. **Better UX**: Users immediately know what's wrong and how to fix it
2. **Reduced Support**: Self-service troubleshooting with clear instructions
3. **Provider Awareness**: Users learn the correct environment variable names
4. **Consistency**: Same format across all providers
5. **Professional**: Rich formatting makes errors feel intentional, not bugs

## Future Enhancements

Potential improvements:
1. Check if `.env` file exists and suggest creating it
2. Validate API key format before making API call
3. Detect common API key issues (e.g., wrong provider's key)
4. Add links to troubleshooting docs
5. Suggest alternative providers if one fails

## Related Issues

This enhancement addresses user feedback about unclear authentication errors and aligns with the project's goal of providing a production-ready, user-friendly LLM abstraction layer.
