# Getting Started with the StratifyAI Web UI

This is the **canonical start-here guide** for launching the Web UI, sending your first message, and enabling advanced browser features like file uploads, streaming, and MCP tools in chat.

**Last Updated:** April 5, 2026

---

## 5-Minute Web UI Quick Start

If you want the fastest route from clone → browser chat, use this checklist.

### 1) Install backend + frontend dependencies

```bash
uv sync
source .venv/bin/activate

cd frontend
npm install
cd ..
```

### 2) Add one provider key

```bash
cp .env.example .env
```

Then open `.env` and set **at least one** provider key, for example:

```bash
OPENAI_API_KEY=your-openai-key
# or
ANTHROPIC_API_KEY=your-anthropic-key
```

### 3) Build the SPA and run the app

```bash
cd frontend
npm run build
cd ..

uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 4) Open the browser

- **Web UI:** `http://localhost:8000`
- **API Docs:** `http://localhost:8000/docs`

### 5) Send your first message

1. Choose a provider and model in the left sidebar.
2. Type a prompt in the chat input.
3. Press **Send** and watch the response stream live.
4. Check token and cost details in the dashboard.

### 6) Optional: enable MCP tools in chat

If you already use Claude Desktop, Cursor, or VS Code MCP configs:

- open **MCP Tools in Chat**
- refresh discovered servers
- enable the servers you want for that conversation
- if a tool appears but is not used, verify the allow-list matches the real tool names (for example `query` or `brave_*`)

### 7) Reset or clear MCP config

The MCP tab now includes a **Reset config** action.

- if one or more configured MCP servers are selected, it removes those entries
- if nothing configured is selected, it clears **all** applied MCP server config for the active client
- it removes both the exported `mcpServers` entries and the matching `stratifyai.mcpClient.servers` metadata block

Use this when you want to quickly recover from a bad config export or start over cleanly.

## Development Mode

Use this setup when working on the Svelte frontend with hot reload.

```bash
# Terminal 1: backend
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: frontend dev server
cd frontend
npm run dev
```

Open the Vite URL shown in the terminal (usually `http://localhost:5173`).

---

# 📘 StratifyAI UI Overview  

**Unified Intelligence Across Every Model Layer**

This document provides a guided walkthrough of the StratifyAI user interface, including the Web UI, Interactive CLI, Model Catalog, and Large‑File Intelligence features. It complements the main README without embedding images directly into PyPI.

---

# 1. Web UI — Overview

The StratifyAI Web UI provides a clean, modern interface for interacting with any supported LLM provider. It mirrors the capabilities of the CLI and Chat surfaces, ensuring full feature parity.

![web ui](../images/stratifyai_webUI.png)

## 1.1 Header

The top of the interface displays:

- The StratifyAI logo  
- The tagline: **Unified Intelligence Across Every Model Layer**  
- The active provider and model  
- Validation status for available models  

This gives users immediate context about the current configuration.

## 1.2 Model Configuration Panel

Located on the left side of the UI.

### Includes:

- **Provider selector**  
  Choose from OpenAI, Anthropic, Google, Groq, DeepSeek, Grok, OpenRouter, Ollama, and AWS Bedrock.

- **Model selector**  
  Models are grouped by quality tier (e.g., Claude Opus 4.5, GPT‑4o‑mini).

- **Temperature control**  
  Adjustable slider for creativity vs. determinism.

- **Max tokens override**  
  Optional field for output length control.

- **Reset Chat**  
  Clears the conversation and resets state.

- **Model validation status**  
  Shows how many models were successfully validated.

This panel ensures that model configuration is always visible and adjustable without interrupting the conversation.

## 1.3 Model Cost Tracking

A dedicated section tracks usage in real time:

- Total context window  
- Number of calls  
- Token usage (input/output)  
- Total cost  
- Button to open the **Model Catalog**

This makes StratifyAI feel like a professional tool — not an opaque system.

## 1.4 Chat Interface

The center panel is the main conversation area.

### Features:

- Markdown rendering  
- Syntax highlighting  
- Code blocks  
- Tables  
- Math formulas  
- Streaming responses  
- Automatic scroll‑to‑latest  

The UI is optimized for long‑form reasoning and technical output.

## 1.5 Input Bar

Located at the bottom:

- Message input  
- File upload  
- “Enable Smart Chunking” toggle  
- Send button  
- Recent message history (last 10 messages)

This creates a smooth workflow for both short prompts and large‑file tasks.

---

# 2. Model Catalog

The Model Catalog provides a searchable, filterable view of all available models across all providers.

![model catalog](../images/stratifyai_webUI_model_catalog.png)

## 2.1 Columns

- **Model name**  
- **Context window**  
- **Input/output cost per million tokens**  
- **Capabilities**  
  - Vision  
  - Tools  
  - Reasoning  
  - Caching  
- **Validation status**

## 2.2 Filters

- Provider  
- Capability  
- Active providers only  
- Validated models only  

This is one of the strongest parts of StratifyAI — it gives users a clear understanding of cost, capability, and performance tradeoffs.

---

# 3. Interactive CLI

The interactive CLI mirrors the Web UI but in a terminal environment.

![Interactive CLI](../images/stratifyai_interactiveUI.png)

### Features:

- Provider and model selection menus  
- Temperature and token controls  
- File loading for context  
- Streaming output  
- Error messages with structured formatting  
- Large‑file detection and chunking  

The CLI is ideal for developers who prefer terminal workflows or need quick testing.

---

# 4. Chat CLI (Large‑File Intelligence)

StratifyAI automatically detects large files and switches into a specialized processing pipeline.

![chat CLI](../images/stratifyai_chatUI.png)

## 4.1 Pipeline

1. **Token‑aware smart chunking**  
2. **Per‑chunk summarization**  
3. **Global synthesis**  
4. **Optional RAG indexing**  
5. **Streaming progress updates**

## 4.2 UI Behavior

- The Web UI shows progress indicators  
- The CLI prints step‑by‑step updates  
- The Chat interface streams chunk summaries  

This makes StratifyAI capable of handling PDFs, logs, codebases, and long documents far beyond typical model limits.

---

# 5. Error Handling

StratifyAI normalizes provider errors into a consistent format.

## 5.1 Error Types

- Authentication errors  
- Rate limits  
- Context window overflow  
- Network issues  
- Routing configuration errors  
- Large‑file processing errors  

## 5.2 UI Presentation

- **Web UI:** toast + expandable details  
- **CLI:** one‑line summary + verbose mode  
- **Chat:** natural‑language summary + technical block  

This makes debugging painless and predictable.

---

# 6. Feature Parity Across Surfaces

StratifyAI ensures that **Web UI**, **Interactive CLI**, and **Chat** all support:

- Routing strategies  
- Model selection  
- Temperature/max token controls  
- File uploads  
- Smart chunking  
- Streaming  
- Error handling  
- Cost tracking  
- Model validation  

This is rare — most frameworks have fragmented UX across surfaces.

---

# 7. Summary

The StratifyAI UI is now:

- Clean  
- Professional  
- Fully featured  
- Consistent across surfaces  
- Optimized for both developers and non‑technical users  

