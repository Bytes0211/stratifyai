# Interactive CLI Demo

This document demonstrates the interactive prompts in the StratifyAI CLI.

## Interactive Chat Command

When you run `chat` without providing required parameters, the CLI will prompt you interactively:

### Example 1: No parameters provided

```bash
$ python -m cli.stratifyai_cli chat

Select Provider
Choose provider (openai/anthropic/google/deepseek/groq/grok/ollama/openrouter) [openai]: anthropic

Available models for anthropic:
  1. claude-sonnet-4-5-20250929
  2. claude-3-7-sonnet-20250219
  3. claude-3-5-sonnet-20241022
  4. claude-3-5-sonnet-20240620
  5. claude-3-5-haiku-20241022
  6. claude-3-opus-20240229
  7. claude-3-sonnet-20240229
  8. claude-3-haiku-20240307
  9. claude-2.1
  10. claude-2.0

Model name: claude-3-5-sonnet-20241022

Temperature (0.0-2.0, default 0.7) [0.7]: 0.8

Enter your message:
Message: Explain quantum computing in simple terms

[Response displayed with cyan formatting]

Cost: $0.002500 | Tokens: 450
```

### Example 2: Partial parameters provided

```bash
$ python -m cli.stratifyai_cli chat -p openai

Available models for openai:
  1. gpt-4o
  2. gpt-4o-mini
  3. gpt-4-turbo
  4. gpt-4
  5. gpt-3.5-turbo
  6. gpt-5
  7. gpt-5-mini
  8. gpt-5-nano
  9. gpt-4.1
  10. gpt-4.1-mini
  ... and 6 more

Model name: gpt-4o-mini

Temperature (0.0-2.0, default 0.7) [0.7]: 1.2

Enter your message:
Message: Write a haiku about coding

[Response displayed with cyan formatting]

Cost: $0.000045 | Tokens: 28
```

### Example 3: Using environment variables

```bash
$ export STRATUMAI_PROVIDER=groq
$ export STRATUMAI_MODEL=llama-3.3-70b
$ python -m cli.stratifyai_cli chat

Temperature (0.0-2.0, default 0.7) [0.7]: 0.9

Enter your message:
Message: What is the capital of France?

[Response displayed with cyan formatting]

Cost: $0.000008 | Tokens: 15
```

### Example 4: All parameters provided (non-interactive)

```bash
$ python -m cli.stratifyai_cli chat -p openai -m gpt-4o-mini -t 0.7 "Hello, world!"

Hello! How can I assist you today?

Cost: $0.000023 | Tokens: 18
```

## Interactive Flow Diagram

```
┌─────────────────────────────────────────┐
│  python -m cli.stratifyai_cli chat      │
└─────────────┬───────────────────────────┘
              │
              ▼
         ┌─────────────┐
         │ Provider?   │────No──▶ Prompt for provider ──┐
         └─────────────┘                                 │
              │Yes                                       │
              ▼                                          │
         ┌─────────────┐◀────────────────────────────────┘
         │ Model?      │────No──▶ Show models + prompt ──┐
         └─────────────┘                                  │
              │Yes                                        │
              ▼                                           │
         ┌─────────────┐◀─────────────────────────────────┘
         │Temperature? │────No──▶ Prompt (default 0.7) ──┐
         └─────────────┘                                  │
              │Yes                                        │
              ▼                                           │
         ┌─────────────┐◀─────────────────────────────────┘
         │ Message?    │────No──▶ Prompt for message ────┐
         └─────────────┘                                  │
              │Yes                                        │
              ▼                                           │
         ┌─────────────┐◀─────────────────────────────────┘
         │ Execute LLM │
         └─────────────┘
              │
              ▼
         Display response
```

## Benefits of Interactive Mode

1. **Beginner-Friendly**: Users don't need to remember all command-line flags
2. **Discoverability**: Shows available providers and models
3. **Guided Experience**: Prompts guide users through required inputs
4. **Flexible**: Can provide parameters via CLI, env vars, or interactively
5. **Smart Defaults**: Uses sensible defaults (e.g., openai provider, 0.7 temperature)

## Tips

- Press `Ctrl+C` at any prompt to cancel
- Use arrow keys to select from choices (provider selection)
- Press Enter to accept default values
- Combine interactive and non-interactive modes as needed

## Comparison: Interactive vs Non-Interactive

| Scenario | Interactive | Non-Interactive |
|----------|-------------|-----------------|
| First-time user | ✅ Easy | ❌ Must know all flags |
| Quick query | ⚠️ More steps | ✅ Fast (one command) |
| Scripting | ❌ Can't script | ✅ Perfect for scripts |
| Learning | ✅ See options | ❌ Need docs |
| Daily use | ⚠️ Ok | ✅ Use env vars + fast |

**Recommendation:** 
- Use interactive mode when exploring or learning
- Use non-interactive mode (with env vars) for daily work
- Use full flags for scripts and automation

---

**Co-Authored-By:** Warp <agent@warp.dev>
