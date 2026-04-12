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

## 4b. Add a Custom MCP Server

If the server you want isn't in the curated catalog, you can add any MCP-compatible server using the Web UI, CLI, or API.

### Web UI (recommended)

1. Open the StratifyAI Web UI and navigate to the **MCP Servers** tab.
2. Click the **Add Custom** tab (next to Catalog).
3. Fill in the form:
   - **Server ID** — a short, lowercase identifier (e.g., `excel`, `my-tools`)
   - **Command** — the executable to run (e.g., `npx`, `python`, `node`)
   - **Arguments** — click "+ Add argument" for each arg
   - **Environment variables** — click "+ Add env var" for key/value pairs
4. Click **Preview config** to review the generated configuration.
5. Click **Apply config** to write it to your selected client's config file.

The server will appear in the Live MCP Client Dashboard where you can start, stop, and test it.

#### Example: Excel MCP Server

| Field | Value |
| ----- | ----- |
| Server ID | `excel` |
| Command | `npx` |
| Argument 1 | `-y` |
| Argument 2 | `@negokaz/excel-mcp-server` |

#### Example: Local Python Server

| Field | Value |
| ----- | ----- |
| Server ID | `my-tools` |
| Command | `python` |
| Argument 1 | `-m` |
| Argument 2 | `my_mcp_server` |
| Env var | `API_KEY` = `your-key-here` |

### CLI

```bash
# Add an npx-based server
uv run stratifyai mcp add-custom excel \
  --client cursor \
  --command npx \
  --command-arg -y \
  --command-arg @negokaz/excel-mcp-server

# Add a local script with env vars
uv run stratifyai mcp add-custom my-tools \
  --client cursor \
  --command python \
  --command-arg -m \
  --command-arg my_mcp_server \
  --env API_KEY=your-key-here
```

### API

```bash
curl -X POST http://127.0.0.1:8080/api/mcp/add-custom \
  -H "Authorization: Bearer $STRATIFYAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "excel",
    "command": "npx",
    "args": ["-y", "@negokaz/excel-mcp-server"],
    "client": "cursor",
    "apply": true
  }'
```

### Managing Custom Servers

Once added, custom servers can be:

- **Edited** — click the pencil icon in the Live Dashboard, or use `PUT /api/mcp/custom/{server_id}`
- **Deleted** — click the trash icon, or use `DELETE /api/mcp/custom/{server_id}`
- **Exported** — click "Export custom" in the Preview & Apply panel, or use `uv run stratifyai mcp export-custom --client cursor`
- **Imported** — click "Import custom" to load a JSON file, or use `uv run stratifyai mcp import-custom --client cursor --file servers.json`

Supported client targets: `claude-desktop`, `claude-code`, `cursor`, `vscode`.

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
