# StratifyAI CLI Usage Guide

Comprehensive guide to using the StratifyAI command-line interface.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or using uv
uv pip install -r requirements.txt
```

## Quick Start

```bash
# Interactive mode - just run chat and you'll be prompted
python -m cli.stratifyai_cli chat

# Or provide some/all parameters
python -m cli.stratifyai_cli chat -p openai
python -m cli.stratifyai_cli chat "Hello, world!"

# Or set environment variables
export STRATUMAI_PROVIDER=openai
export STRATUMAI_MODEL=gpt-4o-mini
python -m cli.stratifyai_cli chat

# Or fully non-interactive
python -m cli.stratifyai_cli chat -p openai -m gpt-4o-mini -t 0.7 "Explain quantum computing"
```

## Commands

### 1. `chat` - Send Chat Message

Send a message to an LLM provider. **All parameters are optional** - if not provided, you'll be prompted interactively!

**Usage:**
```bash
python -m cli.stratifyai_cli chat [OPTIONS] [MESSAGE]
```

**Options:**
- `--provider, -p TEXT`: LLM provider (env: `STRATUMAI_PROVIDER`) *[will prompt if not provided]*
- `--model, -m TEXT`: Model name (env: `STRATUMAI_MODEL`) *[will prompt if not provided]*
- `--temperature, -t FLOAT`: Temperature 0.0-2.0 *[will prompt if not provided, default: 0.7]*
- `--max-tokens INTEGER`: Maximum tokens to generate
- `--stream`: Stream response in real-time
- `--system, -s TEXT`: System message

**Interactive Features:**
- If no provider: Shows list of 8 providers to choose from
- If no model: Displays available models for selected provider
- If no temperature: Prompts with default value (0.7)
- If no message: Prompts for message content

**Conversation Flow:**
After each response, you'll be presented with options:
- **[1] Continue conversation**: Send a follow-up message (maintains context)
- **[2] Save & continue**: Save conversation to markdown and continue
- **[3] Save & exit**: Save conversation to markdown and exit
- **[4] Exit**: Exit without saving

**Note:** For extended multi-turn conversations, use `stratifyai interactive` instead for a better experience.

**Examples:**

```bash
# Interactive mode - will prompt for everything
python -m cli.stratifyai_cli chat

# Partial interactive - provide provider, prompted for rest
python -m cli.stratifyai_cli chat -p anthropic

# Basic usage (fully specified)
python -m cli.stratifyai_cli chat -p anthropic -m claude-sonnet-4-5 "Hello"

# With system message
python -m cli.stratifyai_cli chat -p openai -m gpt-4o-mini \
  --system "You are a helpful coding assistant" \
  "How do I reverse a list in Python?"

# With streaming
python -m cli.stratifyai_cli chat -p groq -m llama-3.3-70b-versatile --stream \
  "Tell me a story"

# With custom temperature
python -m cli.stratifyai_cli chat -p openai -m gpt-4o-mini -t 1.5 \
  "Write a creative poem"

# Using environment variables
export STRATUMAI_PROVIDER=anthropic
export STRATUMAI_MODEL=claude-sonnet-4-5
python -m cli.stratifyai_cli chat "What is the capital of France?"
```

---

### 2. `models` - List Available Models

Display all available models with context window sizes.

**Usage:**
```bash
python -m cli.stratifyai_cli models [OPTIONS]
```

**Options:**
- `--provider, -p TEXT`: Filter by provider

**Examples:**

```bash
# List all models
python -m cli.stratifyai_cli models

# List models for specific provider
python -m cli.stratifyai_cli models --provider openai
python -m cli.stratifyai_cli models -p anthropic
```

**Output:**
```
                            Available Models                            
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Provider     ┃ Model                                    ┃    Context ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ openai       │ gpt-4o-mini                              │    128,000 │
│ openai       │ gpt-4.1                                  │    128,000 │
│ anthropic    │ claude-sonnet-4-5                        │    200,000 │
│ google       │ gemini-2.0-flash-exp                     │  1,000,000 │
└──────────────┴──────────────────────────────────────────┴────────────┘
```

---

### 3. `providers` - List All Providers

Display all available LLM providers.

**Usage:**
```bash
python -m cli.stratifyai_cli providers
```

**Example:**

```bash
python -m cli.stratifyai_cli providers
```

**Output:**
```
                            Available Providers                            
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Provider        ┃     Models ┃ Example Model                            ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ openai          │         16 │ gpt-4o-mini                              │
│ anthropic       │         10 │ claude-sonnet-4-5                        │
│ google          │          7 │ gemini-2.0-flash-exp                     │
│ deepseek        │          2 │ deepseek-chat                            │
│ groq            │          3 │ llama-3.3-70b-versatile                  │
│ grok            │          2 │ grok-2-1212                              │
│ openrouter      │          2 │ anthropic/claude-3.5-sonnet              │
│ ollama          │          3 │ llama3.3                                 │
│ bedrock         │         16 │ anthropic.claude-3-5-sonnet-20241022-v2:0│
└─────────────────┴────────────┴──────────────────────────────────────────┘
```

---

### 4. `route` - Auto-Select Best Model

Use the intelligent router to automatically select the best model based on your query.

**Usage:**
```bash
python -m cli.stratifyai_cli route [OPTIONS] MESSAGE
```

**Options:**
- `--strategy, -s TEXT`: Routing strategy (cost, quality, latency, hybrid) [default: hybrid]
- `--execute, -e`: Execute with selected model without prompting
- `--max-cost FLOAT`: Maximum cost per 1K tokens
- `--max-latency INTEGER`: Maximum latency in milliseconds

**Routing Strategies:**
- `cost`: Select cheapest models (Groq, Google Flash, DeepSeek)
- `quality`: Select best models (GPT-4.1, o3-mini, Claude Sonnet 4.5, Gemini 2.0 Pro)
- `latency`: Select fastest models (Groq, Ollama local models)
- `hybrid`: Dynamically balance based on prompt complexity

**Examples:**

```bash
# Use hybrid strategy (default)
python -m cli.stratifyai_cli route "What is 2+2?"

# Use cost strategy
python -m cli.stratifyai_cli route --strategy cost "Simple question"

# Use quality strategy
python -m cli.stratifyai_cli route --strategy quality \
  "Explain quantum entanglement in detail"

# Use latency strategy
python -m cli.stratifyai_cli route --strategy latency \
  "Quick answer needed"

# Auto-execute without confirmation
python -m cli.stratifyai_cli route --execute "Hello"

# With cost constraint
python -m cli.stratifyai_cli route --max-cost 0.002 "Simple query"

# With latency constraint
python -m cli.stratifyai_cli route --max-latency 1000 "Fast response please"
```

**Output:**
```
Routing Decision
Strategy: hybrid
Complexity: 0.150
Selected: groq/llama-3.3-70b-versatile
Quality: 0.85
Latency: 800ms

Execute with this model? [Y/n]: y

Executing...

2 + 2 = 4

Cost: $0.000050 | Tokens: 12 | Latency: 782ms
```

---

### 5. `interactive` - Interactive Chat Session

Start an interactive chat session with conversation history.

**Usage:**
```bash
python -m cli.stratifyai_cli interactive [OPTIONS]
```

**Options:**
- `--provider, -p TEXT`: LLM provider (env: `STRATUMAI_PROVIDER`)
- `--model, -m TEXT`: Model name (env: `STRATUMAI_MODEL`)

**Examples:**

```bash
# Interactive mode with prompts
python -m cli.stratifyai_cli interactive

# With provider and model specified
python -m cli.stratifyai_cli interactive -p anthropic -m claude-sonnet-4-5

# Using environment variables
export STRATUMAI_PROVIDER=openai
export STRATUMAI_MODEL=gpt-4o-mini
python -m cli.stratifyai_cli interactive
```

**Interactive Session:**
```
StratifyAI Interactive Mode
Provider: openai | Model: gpt-4o-mini
Type 'exit', 'quit', or 'q' to exit

You: Hello
Assistant
Hello! How can I assist you today?
Cost: $0.000123 | Tokens: 25

You: Tell me a joke
Assistant
Why did the programmer quit his job?
Because he didn't get arrays!
Cost: $0.000089 | Tokens: 18

You: exit
Goodbye!
```

---

## Environment Variables

Set these to avoid specifying provider/model on every command:

```bash
export STRATUMAI_PROVIDER=openai        # Default provider
export STRATUMAI_MODEL=gpt-4o-mini      # Default model

# API keys (required for each provider you use)
export OPENAI_API_KEY=your-key-here
export ANTHROPIC_API_KEY=your-key-here
export GOOGLE_API_KEY=your-key-here
export DEEPSEEK_API_KEY=your-key-here
export GROQ_API_KEY=your-key-here
export XAI_API_KEY=your-key-here
export OPENROUTER_API_KEY=your-key-here

# AWS Bedrock credentials (uses boto3)
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key
export AWS_DEFAULT_REGION=us-east-1

# Ollama doesn't require an API key (runs locally)
```

---

## Shell Completion

Install shell completion for bash, zsh, or fish:

```bash
# Bash
python -m cli.stratifyai_cli --install-completion bash

# Zsh
python -m cli.stratifyai_cli --install-completion zsh

# Fish
python -m cli.stratifyai_cli --install-completion fish
```

---

## Tips and Tricks

### 1. Alias for Quick Access

Add to your `.bashrc` or `.zshrc`:

```bash
alias sm="python -m cli.stratifyai_cli"
alias smc="python -m cli.stratifyai_cli chat"
alias smi="python -m cli.stratifyai_cli interactive"
```

Usage:
```bash
sm chat "Hello"
smc "Quick question"
smi
```

### 2. Piping Input

```bash
# Pipe file content
cat file.txt | xargs python -m cli.stratifyai_cli chat -p openai -m gpt-4o

# Use with other commands
echo "Explain docker" | xargs python -m cli.stratifyai_cli chat -p anthropic -m claude-sonnet-4-5
```

### 3. Cost-Effective Usage

```bash
# Use cost strategy for simple queries
python -m cli.stratifyai_cli route --strategy cost --execute "Simple question"

# Set a low-cost model as default
export STRATUMAI_PROVIDER=groq
export STRATUMAI_MODEL=llama-3.3-70b-versatile
```

### 4. Streaming for Long Responses

```bash
# Enable streaming for stories, explanations, code generation
python -m cli.stratifyai_cli chat --stream -p anthropic -m claude-sonnet-4-5 \
  "Write a detailed explanation of machine learning"
```

---

## Troubleshooting

### Provider/Model Required Error

```
Error: --provider (-p) is required or set STRATUMAI_PROVIDER
```

**Solution:** Set environment variables or provide flags:
```bash
export STRATUMAI_PROVIDER=openai
export STRATUMAI_MODEL=gpt-4o-mini
```

### API Key Not Found

```
Error: OpenAI API key not found
```

**Solution:** Set the appropriate API key:
```bash
export OPENAI_API_KEY=your-key-here
```

### Invalid Provider

```
Invalid provider: Provider 'xyz' not supported
```

**Solution:** Check available providers:
```bash
python -m cli.stratifyai_cli providers
```

### Module Not Found Error

```
ModuleNotFoundError: No module named 'typer'
```

**Solution:** Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Comparison with FastAPI Web GUI

| Feature | CLI | Web GUI |
|---------|-----|---------|
| **Speed** | ✅ Instant | ⚠️ Requires server |
| **Streaming** | ✅ Real-time | ✅ WebSocket |
| **Scriptable** | ✅ Yes | ❌ No |
| **Automation** | ✅ Easy | ❌ Difficult |
| **UI** | ⚠️ Terminal | ✅ Browser |
| **Setup** | ✅ Zero config | ⚠️ Server process |
| **Remote access** | ❌ Local only | ✅ Network access |

**Recommendation:** Use CLI for daily developer work, Web GUI for demos/presentations.

---

## Next Steps

- See `docs/adr-cli-interface.md` for architecture decisions
- Check `examples/router_example.py` for router usage
- Read `README.md` for Python library usage
- Review `AGENTS.md` for development setup

---

**Co-Authored-By:** Warp <agent@warp.dev>
