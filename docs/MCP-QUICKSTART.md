# MCP Server Quickstart

Get StratifyAI working as an MCP server in under 15 minutes.

---

## 1. Install

```bash
# Install with MCP support
pip install -e ".[mcp]"

# Or with uv
uv sync --extra mcp
```

## 2. Set API Keys

Set at least one provider key in your environment:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
# Optional: GOOGLE_API_KEY, DEEPSEEK_API_KEY, GROQ_API_KEY, etc.
```

## 3. Verify It Works

```bash
# Start the server directly
stratifyai-mcp

# Or run as a module
python -m stratifyai.mcp_server
```

The server runs on stdio by default. Press Ctrl+C to stop.

## 4. Connect a Client

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "stratifyai": {
      "command": "stratifyai-mcp",
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

### Claude Code

```bash
claude mcp add stratifyai stratifyai-mcp
```

See [MCP-CLIENT-CONFIG.md](MCP-CLIENT-CONFIG.md) for more clients (Cursor, VS Code, etc.).

## 5. Try It Out

Once connected, ask your MCP client:

- "List all available providers" (calls `list_providers`)
- "What models does OpenAI offer?" (calls `list_models`)
- "Estimate the cost of sending 1000 words to gpt-4o" (calls `estimate_cost`)
- "Send 'Hello world' to openai/gpt-4o-mini" (calls `chat_completion`)

## Available Tools

| Tool | Description |
|------|-------------|
| `chat_completion` | Send a chat request to a specific provider/model |
| `chat_with_routing` | Auto-route to the best model using a strategy |
| `list_providers` | List providers with config status |
| `list_models` | List models for a provider |
| `get_model_info` | Get full metadata for a model |
| `get_cost_summary` | Session cost breakdown |
| `validate_provider` | Check if a provider is configured |
| `estimate_cost` | Estimate token count and cost |

See [MCP-TOOLS-REFERENCE.md](MCP-TOOLS-REFERENCE.md) for full input/output schemas.

## Available Resources

| URI | Description |
|-----|-------------|
| `stratifyai://catalog` | Full model catalog |
| `stratifyai://catalog/{provider}` | Models for one provider |
| `stratifyai://providers` | Provider list with status |
| `stratifyai://costs` | Session cost summary |
| `stratifyai://router/strategies` | Routing strategy descriptions |

## Troubleshooting

**Server won't start:**
- Ensure `mcp` is installed: `pip install "mcp[cli]>=1.25,<2"`
- Check Python version is 3.10+

**"API key not set" errors:**
- Set the environment variable for your provider (see step 2)
- Use `validate_provider` to check configuration

**Client can't find server:**
- Ensure `stratifyai-mcp` is on your PATH
- Try the full path: `which stratifyai-mcp`
