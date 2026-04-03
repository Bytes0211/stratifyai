# MCP Client Configuration

How to connect various MCP clients to the StratifyAI MCP server.

---

## Prerequisites

```bash
# Install StratifyAI with MCP support
pip install -e ".[mcp]"

# Verify the command is available
stratifyai-mcp --help
```

Set your provider API keys as environment variables (at minimum one):

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

---

## Claude Desktop

Add to your Claude Desktop config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

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

Restart Claude Desktop after saving.

---

## Claude Code

```bash
# Add the server
claude mcp add stratifyai stratifyai-mcp

# Or with environment variables
claude mcp add stratifyai stratifyai-mcp \
  -e OPENAI_API_KEY=sk-... \
  -e ANTHROPIC_API_KEY=sk-ant-...

# Verify
claude mcp list
```

---

## Cursor

Add to `.cursor/mcp.json` in your project root:

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

---

## VS Code (Copilot Chat)

Add to your VS Code `settings.json`:

```json
{
  "mcp": {
    "servers": {
      "stratifyai": {
        "command": "stratifyai-mcp",
        "env": {
          "OPENAI_API_KEY": "sk-...",
          "ANTHROPIC_API_KEY": "sk-ant-..."
        }
      }
    }
  }
}
```

---

## Windsurf / Warp

Both support the same MCP config format. Add to the tool's MCP config file:

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

Refer to each tool's documentation for the config file location.

---

## Using a Virtual Environment

If StratifyAI is installed in a virtual environment, use the full path:

```json
{
  "mcpServers": {
    "stratifyai": {
      "command": "/path/to/your/venv/bin/stratifyai-mcp",
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

Find the path with:

```bash
which stratifyai-mcp
```

---

## Transport Options

By default, the server uses stdio transport. For remote scenarios (post-GA):

```json
{
  "mcpServers": {
    "stratifyai": {
      "command": "stratifyai-mcp",
      "args": ["--transport", "streamable-http"]
    }
  }
}
```

---

## Troubleshooting

**"command not found":**
- Ensure the virtualenv is activated, or use the full path to `stratifyai-mcp`

**"No tools found":**
- Check that `mcp` extra is installed: `pip install -e ".[mcp]"`
- Restart your MCP client after config changes

**Authentication errors:**
- Verify API keys are set in the `env` block of your config
- Use the `validate_provider` tool to check configuration
