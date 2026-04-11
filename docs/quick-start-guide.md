# StratifyAI Quick Start Guide

Get the StratifyAI Web UI running in under 5 minutes.

**Last Updated:** April 11, 2026 | **Version:** 2.1.0

---

## Prerequisites

| Dependency | Version | Check |
|------------|---------|-------|
| **Python** | 3.10+ | `python3 --version` |
| **Node.js** | 18+ | `node --version` |
| **uv** | latest | `uv --version` |

### Install uv (if needed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Node.js (if needed)

```bash
# Ubuntu/Debian
sudo apt install nodejs npm

# macOS
brew install node
```

---

## Step 1: Install StratifyAI

```bash
uv pip install stratifyai
```

Or install from source:

```bash
git clone https://github.com/Bytes0211/stratifyai.git
cd stratifyai
uv sync
```

---

## Step 2: Configure an API Key

Create a `.env` file in the project root with at least one provider key:

```bash
cp .env.example .env
```

Edit `.env` and add your key:

```bash
# Pick one (or add multiple)
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
GOOGLE_API_KEY=your-key-here

# Required for the Web UI API
STRATIFYAI_API_KEY=any-secret-string-you-choose
```

Verify your keys are configured:

```bash
uv run stratifyai check-keys
```

You should see at least one provider reported as **Configured**.

---

## Step 3: Build the Frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

This compiles the Svelte SPA into `api/static/dist/`.

---

## Step 4: Start the Server

```bash
uv run uvicorn api.main:app --host 127.0.0.1 --port 8080
```

You should see output like:

```
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```

---

## Step 5: Open the Web UI

Open your browser to **http://127.0.0.1:8080**

### Send your first message

1. Select a **provider** and **model** in the sidebar (e.g., OpenAI / gpt-4o-mini).
2. Type a prompt in the chat input.
3. Press **Send** and watch the response stream in real time.
4. Check token usage and cost in the dashboard.

---

## What You Can Do in the Web UI

### Chat

- Stream responses from any configured provider
- Switch models mid-conversation
- Upload files for analysis (drag-and-drop or browse)
- View token counts and cost per message

### MCP Servers

- Browse and configure curated MCP integrations from the catalog
- Add custom MCP servers (command, args, env vars)
- Start/stop/restart servers from the live dashboard
- Test tools directly and manage permissions

### Configuration

- Compare models across providers
- Set temperature, max tokens, and routing strategy
- View provider status and API key health

---

## Common Server Options

```bash
# Development mode with auto-reload
uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8080

# Allow access from other machines on your network
uv run uvicorn api.main:app --host 0.0.0.0 --port 8080

# Run on a different port
uv run uvicorn api.main:app --host 127.0.0.1 --port 3000
```

---

## CLI (Optional)

StratifyAI also includes a CLI for quick tasks without the browser:

```bash
# One-shot chat
uv run stratifyai chat -p openai -m gpt-4o-mini -t "Say hello"

# Interactive mode
uv run stratifyai interactive

# Check MCP server status with cursor MCP Server
uv run stratifyai mcp status --client cursor

# Check MCP server status with cursor MCP Server
uv run stratifyai mcp status --client claude-desktop 
```

---

## Troubleshooting

### "Module not found" or import errors

Make sure you installed dependencies:

```bash
uv sync              # backend
cd frontend && npm install && npm run build && cd ..  # frontend
```

### Web UI shows a blank page

The frontend hasn't been built. Run `npm run build` in the `frontend/` directory.

### "401 Unauthorized" in the browser

Set `STRATIFYAI_API_KEY` in your `.env` file. The Web UI needs this to authenticate API requests.

### Provider returns errors

Run `uv run stratifyai check-keys` to verify your provider API keys are valid.

---

## Next Steps

- **Full documentation:** `docs/GETTING-STARTED.md`
- **Web UI guide:** `docs/UI-OVERVIEW.md`
- **API reference:** `docs/API-REFERENCE.md`
- **MCP setup:** `docs/MCP-QUICKSTART.md`
- **Examples:** `examples/README.md`
