# PRD: StratifyAI Phase 8 — Bug Fixes, Web UI Redesign, MCP Server

**Version:** 1.0
**Date:** 2026-02-15
**Author:** Steven Cotton
**Current Phase:** 7.9 Complete
**Target Phase:** 8.0

---

## Table of Contents

1. [Section 1: Bug Fixes](#section-1-bug-fixes)
2. [Section 2: Web UI Redesign](#section-2-web-ui-redesign)
3. [Section 3: MCP Server Implementation](#section-3-mcp-server-implementation)

---

## Section 1: Bug Fixes

### Overview

Code review of the StratifyAI codebase identified 14 bugs across the API layer, provider implementations, configuration, and core modules. Bugs are prioritized by severity and grouped by subsystem.

---

### 1.1 Critical Bugs

#### BUG-001: WebSocket Streaming Does Not Track Costs

- **File:** `api/main.py:607-621`
- **Description:** The REST endpoint (`POST /api/chat`) tracks costs via `cost_tracker.add_entry()` (line 446), but the WebSocket streaming endpoint (`/api/chat/stream`) has zero cost tracking. All streaming conversations are untracked, causing inaccurate cost reports.
- **Impact:** Users relying on cost tracking will see incomplete data. Budget alerts won't fire for streaming requests.
- **Fix:** After the streaming loop completes, extract usage data from the stream's final message (or accumulate from chunks) and call `cost_tracker.add_entry()`.
- **Acceptance Criteria:**
  - WebSocket streaming requests appear in cost tracking summary
  - Cost-by-provider and cost-by-model include streaming requests
  - Budget alerts fire for streaming costs

#### BUG-002: Reasoning Model Detection Inconsistency

- **File:** `api/main.py:410-419` vs `api/main.py:574-582`
- **Description:** The REST chat endpoint includes `gpt-5` in its reasoning model name pattern (line 415: `model_lower.startswith("gpt-5")`), but the WebSocket endpoint does NOT include this pattern (line 578). This means GPT-5 requests via streaming won't get the required `temperature=1.0` override, potentially causing API errors.
- **Also duplicated in:** `stratifyai/providers/openai_compatible.py:129-138` (includes gpt-5 pattern)
- **Impact:** Streaming requests to GPT-5 models will send incorrect temperature, causing API failures or degraded output.
- **Fix:** Extract reasoning model detection into a shared utility function. All three call sites should use the single source of truth.
- **Acceptance Criteria:**
  - Single `is_reasoning_model(provider, model, model_catalog)` function in `stratifyai/utils/`
  - All three call sites (REST, WebSocket, OpenAI-compatible provider) use the shared function
  - GPT-5 pattern detected consistently across all code paths

---

### 1.2 High-Severity Bugs

#### BUG-003: LLMClient Created Per Request (No Connection Pooling)

- **Files:** `api/main.py:303`, `api/main.py:442`, `api/main.py:605`
- **Description:** A new `LLMClient` (and underlying HTTP client via `AsyncOpenAI` or `AsyncAnthropic`) is created for every single API request. This prevents HTTP connection pooling, increases latency, and creates unnecessary garbage collection pressure.
- **Impact:** Performance degradation under load. Each request incurs TCP handshake + TLS setup overhead.
- **Fix:** Create a provider-keyed client cache at module level. Reuse `LLMClient` instances per provider.
- **Acceptance Criteria:**
  - Clients are cached by provider name and reused across requests
  - Connection pooling is active (verify via response latency improvement)
  - Cache handles provider configuration changes gracefully

#### BUG-004: CORS Wildcard with Credentials is Invalid

- **File:** `api/main.py:36-41`
- **Description:** `allow_origins=["*"]` combined with `allow_credentials=True` violates the CORS specification (RFC 6454). Some browsers will reject credentialed requests entirely.
- **Impact:** Cross-origin requests with cookies/auth headers may silently fail in certain browsers.
- **Fix:** Either remove `allow_credentials=True` (current UI doesn't need credentials), or replace the wildcard with specific allowed origins configurable via environment variable.
- **Acceptance Criteria:**
  - CORS configuration is spec-compliant
  - `CORS_ALLOWED_ORIGINS` env var available for production configuration
  - Default remains permissive for development (`["http://localhost:8080", "http://localhost:5173"]`)

#### BUG-005: WebSocket `finally` Block Double-Close

- **File:** `api/main.py:631-632`
- **Description:** The `finally` block unconditionally calls `await websocket.close()`. If the WebSocket was already disconnected (caught by `WebSocketDisconnect` on line 623), this will raise a `RuntimeError` because the connection is already closed.
- **Impact:** Unhandled exception in the `finally` block. May cause error log noise and mask the original disconnect reason.
- **Fix:** Wrap the `close()` call in a try/except, or check connection state before closing.
- **Acceptance Criteria:**
  - No `RuntimeError` when client disconnects mid-stream
  - Clean disconnect handling in server logs

#### BUG-006: Stale Summarization Model Reference (`grok-beta`)

- **File:** `api/main.py:296`
- **Description:** The `summarization_models` dictionary maps `grok` provider to `grok-beta`, but this model is no longer in the current Grok catalog. The current models are `grok-4-1-fast-non-reasoning`, `grok-3`, etc.
- **Impact:** Smart chunking will fail for Grok provider with an `InvalidModelError` when attempting file summarization.
- **Fix:** Update to a valid, low-cost Grok model (e.g., `grok-4-1-fast-non-reasoning` or `grok-3-mini`).
- **Acceptance Criteria:**
  - All summarization model references point to valid models in `catalog/models.json`
  - Smart chunking works for all 9 providers

---

### 1.3 Medium-Severity Bugs

#### BUG-007: `asyncio.get_event_loop()` Deprecated

- **File:** `api/main.py:156`
- **Description:** `asyncio.get_event_loop()` is deprecated in Python 3.10+ and emits `DeprecationWarning`. In Python 3.12+, it raises an error if no running loop exists.
- **Fix:** Replace with `asyncio.get_running_loop()` (safe inside async context).
- **Acceptance Criteria:** No deprecation warnings. Compatible with Python 3.10-3.12+.

#### BUG-008: ThreadPoolExecutor Created Per Request

- **Files:** `api/main.py:157-162`, `api/main.py:687-688`
- **Description:** A new `ThreadPoolExecutor()` is created for every request to `/api/models/{provider}` and `/api/all-models`. Creating thread pools is expensive.
- **Fix:** Create a module-level shared executor. Or better, convert `get_validated_interactive_models` to async to avoid the executor entirely.
- **Acceptance Criteria:** Single shared executor, or fully async validation.

#### BUG-009: Version String Mismatch

- **Files:** `api/main.py:31` ("0.1.0"), `api/main.py:100` ("0.1.0"), `pyproject.toml` ("0.1.3"), `api/main.py:751` ("0.1.0")
- **Description:** API version is hardcoded as "0.1.0" in three places while `pyproject.toml` declares "0.1.3".
- **Fix:** Read version from `pyproject.toml` or `stratifyai.__version__` at startup. Single source of truth.
- **Acceptance Criteria:** `/api/health` returns the correct version matching `pyproject.toml`.

#### BUG-010: Router Quality/Latency Scores Are Stale

- **File:** `stratifyai/router.py:64-147`
- **Description:** Quality scores and latency estimates are hardcoded for a small subset of models. Many catalog models default to 0.75 quality and 2000ms latency. Several referenced models no longer exist (e.g., `gpt-4.5-turbo-20250205`, `claude-sonnet-4-5-20250929`, `claude-haiku-4-5`). New models (Grok 4, Claude Sonnet 4, Gemini 3) have no entries.
- **Impact:** Routing decisions are inaccurate for most models. The router may select suboptimal models.
- **Fix:** Move quality/latency metadata into `catalog/models.json` alongside cost data. Router reads from catalog instead of hardcoded dicts.
- **Acceptance Criteria:**
  - Quality scores and latency estimates are in `catalog/models.json`
  - Router reads from catalog (no hardcoded dicts)
  - All catalog models have quality/latency metadata

#### BUG-011: `cache_response` Decorator Mutates Shared TTL

- **File:** `stratifyai/caching.py:221`
- **Description:** `cache.ttl = ttl` mutates the global cache instance's TTL. If multiple decorators use different TTLs (e.g., `@cache_response(ttl=60)` and `@cache_response(ttl=3600)`), the last-applied decorator overrides the TTL for all cached entries.
- **Fix:** Store TTL per-entry (already in `CacheEntry.timestamp`), and check against the decorator's TTL on retrieval rather than mutating the global.
- **Acceptance Criteria:** Different cache decorators can specify different TTLs without interference.

#### BUG-012: Type Hint `any` Instead of `Any`

- **Files:** `stratifyai/cost_tracker.py:165`, `stratifyai/cost_tracker.py:192`, `stratifyai/cost_tracker.py:241`
- **Description:** Uses lowercase `any` (Python builtin) instead of `typing.Any` in `Dict[str, any]` type hints. While this works at runtime in Python 3.10+, it's incorrect for static type checkers and inconsistent with the rest of the codebase.
- **Fix:** Replace `any` with `Any` from `typing`.
- **Acceptance Criteria:** All type hints use `typing.Any`. `mypy` passes without errors on these files.

---

### 1.4 Low-Severity Bugs

#### BUG-013: WebSocket Endpoint Missing Feature Parity

- **File:** `api/main.py:540-632`
- **Description:** The WebSocket streaming endpoint is missing several features present in the REST endpoint:
  - No file upload handling (`file_content`, `file_name`)
  - No token limit validation (lines 343-403 in REST)
  - No smart chunking support
- **Impact:** Users streaming with files attached will get raw (possibly too-large) content without chunking or validation.
- **Fix:** Extract shared logic (file handling, token validation, chunking) into helper functions. Call from both endpoints.
- **Acceptance Criteria:**
  - WebSocket endpoint supports file uploads with chunking
  - Token limit validation runs for WebSocket requests
  - Shared helper functions eliminate code duplication between REST and WebSocket

#### BUG-014: Port Mismatch Between Code and Documentation

- **Files:** `api/main.py:759` (port 8000), documentation references port 8080
- **Description:** The `uvicorn.run()` call uses port 8000, but `start_app.sh` and multiple docs reference port 8080.
- **Fix:** Centralize port configuration via `STRATIFYAI_PORT` env var with default 8080. Update `__main__` block to read from env.
- **Acceptance Criteria:** Port is configurable and defaults match documentation.

---

### 1.5 Bug Fix Implementation Priority

| Priority | Bug ID | Effort | Description |
|----------|--------|--------|-------------|
| P0 | BUG-001 | Medium | WebSocket cost tracking |
| P0 | BUG-002 | Low | Reasoning model detection consolidation |
| P1 | BUG-003 | Medium | Client connection pooling |
| P1 | BUG-004 | Low | CORS configuration |
| P1 | BUG-005 | Low | WebSocket double-close |
| P1 | BUG-006 | Low | Stale model references |
| P2 | BUG-007 | Low | Deprecated asyncio API |
| P2 | BUG-008 | Low | ThreadPoolExecutor per request |
| P2 | BUG-009 | Low | Version mismatch |
| P2 | BUG-010 | Medium | Router stale metadata |
| P2 | BUG-011 | Low | Cache TTL mutation |
| P2 | BUG-012 | Low | Type hint fix |
| P3 | BUG-013 | High | WebSocket feature parity |
| P3 | BUG-014 | Low | Port configuration |

---

## Section 2: Web UI Redesign

### Overview

Replace the current vanilla HTML/CSS/JS web UI (2 monolithic HTML files, ~67KB combined, embedded CSS) with a modern component-based architecture using **Svelte 5**, **Vite**, and **SASS**.

### Objectives

1. **Maintainability:** Break monolithic HTML into composable components with scoped styles
2. **Design:** Dark-first AI Studio aesthetic with light mode toggle
3. **Accessibility:** WCAG 2.1 AA compliance via Bits UI headless primitives
4. **Performance:** Compiled Svelte (no runtime framework), optimized builds, connection pooling
5. **Developer Experience:** Hot module replacement, SASS design tokens, component isolation

---

### 2.1 Technical Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Framework** | Svelte 5 (Runes) | Compiles away — zero runtime. Runes reactivity ideal for streaming chat. Closest to vanilla JS learning curve. Production-stable since Oct 2024 (v5.28+). |
| **Build Tool** | Vite | Native Svelte + SASS support. Sub-second HMR. Optimized production builds. ~15 lines of config. |
| **Styling** | SASS (flat structure) + Svelte scoped styles | Design tokens, mixins, theming via CSS custom properties. Component styles scoped automatically. |
| **A11y Primitives** | Bits UI | Headless (unstyled) accessible components for Dialog, Select, Tabs, Tooltip, Toast. Zero visual opinion — all styling from scratch via SASS. |
| **Icons** | Lucide Svelte | Tree-shakeable SVG icons. Consistent weight/style. 1500+ icons. |
| **Typography** | Inter + JetBrains Mono | Inter: modern, excellent readability. JetBrains Mono: code-optimized with ligatures. |
| **Serving** | FastAPI `StaticFiles` | `vite build` outputs to `api/static/dist/`. FastAPI serves SPA with catch-all route. No separate deployment. |

---

### 2.2 Design Language: Dark-First AI Studio

#### Color System

```scss
// Background layers (dark mode)
$bg-base:        #0f172a;   // Deepest background
$bg-surface:     #1e293b;   // Card/panel surfaces
$bg-elevated:    #334155;   // Elevated elements (dropdowns, modals)
$bg-hover:       #475569;   // Hover states

// Text hierarchy
$text-primary:   #f8fafc;   // Main content
$text-secondary: #94a3b8;   // Supporting text
$text-muted:     #64748b;   // Disabled/placeholder

// Primary accent
$accent-primary: #06b6d4;   // Teal/cyan — CTAs, active states
$accent-hover:   #22d3ee;   // Lighter teal for hover

// Provider brand colors (contextual accents)
$provider-openai:      #10a37f;
$provider-anthropic:   #d4a574;
$provider-google:      #4285f4;
$provider-deepseek:    #4f6ef7;
$provider-groq:        #f55036;
$provider-grok:        #1d9bf0;
$provider-openrouter:  #8b5cf6;
$provider-ollama:      #ffffff;
$provider-bedrock:     #ff9900;

// Semantic colors
$success:  #22c55e;
$warning:  #f59e0b;
$error:    #ef4444;
$info:     #3b82f6;
```

#### Typography

```scss
$font-sans:  'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
$font-mono:  'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace;

$text-xs:    0.75rem;   // 12px - badges, labels
$text-sm:    0.875rem;  // 14px - secondary text
$text-base:  1rem;      // 16px - body
$text-lg:    1.125rem;  // 18px - subheadings
$text-xl:    1.25rem;   // 20px - headings
$text-2xl:   1.5rem;    // 24px - page titles
```

#### Design Principles

1. **Dense but breathable** — Information-rich layouts with consistent spacing tokens
2. **Glass morphism** — Subtle `backdrop-filter: blur()` on elevated surfaces
3. **Micro-animations** — Smooth transitions for message appearance, loading states, panel toggles (150-300ms, ease-out)
4. **Provider identity** — Color-coded badges/chips for each provider throughout the UI
5. **Dark-first with light toggle** — CSS custom properties swap color tokens via `[data-theme="light"]`

---

### 2.3 SASS Architecture (Flat Structure)

```
frontend/
  src/
    styles/
      _tokens.scss       # Design tokens: colors, spacing, typography, shadows, radii
      _mixins.scss        # Responsive breakpoints, truncation, scrollbar styling
      _reset.scss         # Modern CSS reset (Andy Bell's reset or similar)
      _base.scss          # Base element styles: body, headings, links, code
      _themes.scss        # Dark/light theme definitions via CSS custom properties
      main.scss           # Imports all partials, applies global styles
```

Component-level styles use Svelte's built-in `<style lang="scss">` with access to global tokens via `@use '../styles/tokens'`.

---

### 2.4 Component Architecture

```
frontend/
  src/
    lib/
      components/
        layout/
          AppShell.svelte          # Main app layout (sidebar + content)
          Header.svelte            # Top bar with logo, theme toggle, nav
          Sidebar.svelte           # Collapsible sidebar container
        chat/
          ChatContainer.svelte     # Chat message list + scroll management
          ChatMessage.svelte       # Individual message (user/assistant/system/error)
          ChatInput.svelte         # Message input with file upload
          MarkdownRenderer.svelte  # Markdown → HTML with syntax highlighting
          StreamingIndicator.svelte # Typing/streaming animation
        config/
          ModelSelector.svelte     # Provider + model selection (Bits UI Select)
          TemperatureSlider.svelte  # Temperature control with reasoning model lock
          TokenConfig.svelte       # Max tokens, chunking toggle
          ProviderBadge.svelte     # Color-coded provider chip
        catalog/
          ModelCatalog.svelte      # Full model catalog page
          ModelCard.svelte         # Individual model with metadata
          ModelFilters.svelte      # Filter by provider, capability, cost
          CapabilityBadge.svelte   # Vision, tools, reasoning badges
        dashboard/
          CostDashboard.svelte     # Cost tracking overview
          CostChart.svelte         # Cost visualization
          UsageSummary.svelte      # Token usage breakdown
        shared/
          Button.svelte            # Base button with variants
          Badge.svelte             # Status/label badge
          Toast.svelte             # Notification toasts (Bits UI)
          LoadingSpinner.svelte    # Loading indicator
          ThemeToggle.svelte       # Dark/light mode switch
      stores/
        chat.svelte.ts             # Chat state (messages, streaming status)
        config.svelte.ts           # Model config (provider, model, temperature)
        cost.svelte.ts             # Cost tracking state
        theme.svelte.ts            # Theme preference (persisted to localStorage)
      api/
        client.ts                  # HTTP client for REST endpoints
        websocket.ts               # WebSocket client for streaming
        types.ts                   # TypeScript interfaces matching API models
      utils/
        markdown.ts                # Markdown rendering configuration
        format.ts                  # Number/currency/date formatting
    routes/
      +page.svelte                 # Chat page (home)
      models/
        +page.svelte               # Model catalog page
    app.html                       # SPA entry point
    app.scss                       # Root SASS import
  vite.config.ts                   # Vite configuration
  svelte.config.js                 # Svelte compiler configuration
  package.json                     # Frontend dependencies
  tsconfig.json                    # TypeScript configuration
```

---

### 2.5 Build Integration with FastAPI

```
# vite.config.ts
export default defineConfig({
  plugins: [svelte()],
  build: {
    outDir: '../api/static/dist',
    emptyOutDir: true,
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `@use 'src/styles/tokens' as *;`
      }
    }
  }
})
```

**FastAPI changes** (`api/main.py`):
- Mount `api/static/dist` instead of `api/static`
- Add catch-all route returning `index.html` for SPA client-side routing
- Preserve `/api/*` routes as-is

**Development workflow:**
- `cd frontend && npm run dev` — Vite dev server with HMR (proxies `/api/*` to FastAPI)
- `cd frontend && npm run build` — Production build to `api/static/dist/`
- `npm run preview` — Preview production build locally

---

### 2.6 Key Interactions

#### Streaming Chat (Svelte 5 Runes + WebSocket)

```svelte
<script>
  let messages = $state([]);
  let isStreaming = $state(false);
  let currentContent = $state('');

  async function sendMessage(text) {
    messages.push({ role: 'user', content: text });
    isStreaming = true;

    const ws = new WebSocket('/api/chat/stream');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.done) {
        messages.push({ role: 'assistant', content: currentContent });
        currentContent = '';
        isStreaming = false;
      } else {
        currentContent += data.content;
      }
    };
    ws.send(JSON.stringify({ provider, model, messages, temperature }));
  }
</script>
```

#### Theme Toggle (CSS Custom Properties)

```scss
// _themes.scss
:root, [data-theme="dark"] {
  --bg-base: #{$bg-base};
  --text-primary: #{$text-primary};
  --accent: #{$accent-primary};
}

[data-theme="light"] {
  --bg-base: #ffffff;
  --text-primary: #0f172a;
  --accent: #0891b2;
}
```

---

### 2.7 Accessibility Requirements

| Component | Approach | Standard |
|-----------|----------|----------|
| Dialog/Modal | Bits UI Dialog | Focus trap, Escape close, ARIA dialog |
| Select/Dropdown | Bits UI Select | Keyboard nav, ARIA listbox, type-ahead |
| Tabs | Bits UI Tabs | Arrow key nav, ARIA tabpanel |
| Tooltip | Bits UI Tooltip | Hover/focus timing, ARIA describedby |
| Toast | Bits UI Toast | ARIA live region, auto-dismiss |
| Chat messages | Semantic HTML | ARIA log role, new message announcements |
| Color contrast | SASS tokens | 4.5:1 minimum ratio (AA) |
| Keyboard nav | Global | All interactive elements focusable, visible focus rings |

---

### 2.8 Migration Plan

| Phase | Scope | Deliverable |
|-------|-------|-------------|
| **Phase A** | Scaffold Vite + Svelte project, SASS tokens, base styles, theme toggle | Empty SPA served by FastAPI |
| **Phase B** | Chat interface: ChatContainer, ChatMessage, ChatInput, streaming, markdown rendering | Feature-parity chat (no config panel) |
| **Phase C** | Config panel: ModelSelector, TemperatureSlider, TokenConfig, file upload | Full chat page feature parity |
| **Phase D** | Model catalog page: ModelCatalog, ModelCard, filters, provider validation | Feature-parity catalog |
| **Phase E** | Cost dashboard, polish, animations, responsive design, accessibility audit | Complete redesign |
| **Phase F** | Remove old HTML files, update documentation, final QA | Clean cutover |

---

## Section 3: MCP Server Implementation

### Overview

Implement a Model Context Protocol (MCP) server that exposes StratifyAI's multi-provider LLM capabilities to MCP-compatible clients (Claude Desktop, Cursor, VS Code, Claude Code, Windsurf, etc.).

### Why MCP?

MCP is the emerging standard for connecting AI models to external tools and data. By implementing an MCP server, StratifyAI becomes usable as a **tool** from within any MCP-compatible AI assistant, enabling:

- **AI-assisted model selection** — An AI agent can query StratifyAI's router to find the optimal model for a task
- **Cross-provider chat from any MCP client** — Use Claude Desktop to send requests through StratifyAI to any of 9 providers
- **Cost awareness in AI workflows** — Agents can check costs before/after making LLM calls
- **RAG integration** — AI agents can index documents and query the RAG pipeline

### Industry Adoption

MCP is widely adopted as of early 2026:
- **Clients:** Claude Desktop, Claude Code, Cursor, VS Code (Copilot), Windsurf, Zed, Replit, Sourcegraph, JetBrains IDEs
- **Protocol:** Open standard by Anthropic, actively maintained
- **Python SDK:** `mcp` package with `FastMCP` 3.0 (released Jan 2026) — mature, production-ready
- **Transport:** stdio (local clients), SSE, Streamable HTTP

---

### 3.1 Technical Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **SDK** | FastMCP (official MCP Python SDK) | 3.0+ |
| **Transport** | stdio (primary), Streamable HTTP (secondary) | MCP spec |
| **Dependencies** | `mcp[cli]` | Add to `pyproject.toml` |
| **Integration** | Reuses existing `stratifyai/` core modules | No architecture changes |

---

### 3.2 MCP Primitives

#### Tools (Model-Controlled)

Tools are functions the AI model can call. These are the primary interface.

| Tool Name | Description | Parameters | Returns |
|-----------|-------------|------------|---------|
| `chat_completion` | Send a chat request to any provider/model | `provider`, `model`, `messages[]`, `temperature?`, `max_tokens?` | Response content, usage stats, cost |
| `chat_with_routing` | Send a chat request using intelligent routing | `messages[]`, `strategy?` (cost/quality/latency/hybrid), `capabilities?[]` | Response content + selected provider/model |
| `list_providers` | List all available LLM providers | None | Provider names with active/inactive status |
| `list_models` | List models for a provider | `provider` | Model IDs with metadata (cost, context, capabilities) |
| `get_model_info` | Get detailed model information | `provider`, `model` | Full metadata: cost, context window, capabilities, reasoning status |
| `get_cost_summary` | Get cost tracking report | `provider?`, `model?` | Total cost, tokens, calls, breakdown by provider/model |
| `validate_provider` | Check if a provider is configured and accessible | `provider` | Active status, available models, API key status |
| `estimate_cost` | Estimate cost for a request before sending | `provider`, `model`, `message_text` | Estimated input tokens, projected cost |

#### Resources (Application-Controlled)

Resources provide context data to the AI model.

| Resource URI | Description | Content |
|-------------|-------------|---------|
| `stratifyai://catalog` | Full model catalog | All providers and models with metadata (JSON) |
| `stratifyai://catalog/{provider}` | Provider-specific catalog | Models for one provider (JSON) |
| `stratifyai://providers` | Provider availability status | Which providers have valid API keys configured |
| `stratifyai://costs` | Current session cost report | Cost summary with breakdown |
| `stratifyai://router/strategies` | Available routing strategies | Strategy descriptions and parameters |

#### Prompts (User-Controlled)

Prompts are templates users can invoke via slash commands or UI elements.

| Prompt Name | Description | Arguments |
|-------------|-------------|-----------|
| `compare_models` | Compare capabilities and costs of models | `models[]` (list of provider/model pairs) |
| `recommend_model` | Get a model recommendation for a task | `task_description`, `budget?`, `priority?` (cost/quality/speed) |
| `analyze_costs` | Analyze spending patterns and suggest optimizations | `time_period?` |

---

### 3.3 Architecture

```
stratifyai/
  mcp_server/
    __init__.py
    server.py              # FastMCP server definition, tool/resource/prompt registration
    tools.py               # Tool implementations (thin wrappers around core modules)
    resources.py           # Resource implementations
    prompts.py             # Prompt template definitions
```

**Key principle:** The MCP server is a thin transport layer. All business logic lives in existing core modules (`LLMClient`, `Router`, `CostTracker`, `config`). The MCP tools are simple wrappers that:
1. Accept MCP-formatted parameters
2. Call existing StratifyAI functions
3. Return formatted results

Example tool implementation:

```python
from mcp.server.fastmcp import FastMCP
from stratifyai import LLMClient, ChatRequest, Message

mcp = FastMCP("stratifyai")

@mcp.tool()
async def chat_completion(
    provider: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> str:
    """Send a chat completion request to any LLM provider via StratifyAI.

    Args:
        provider: LLM provider (openai, anthropic, google, deepseek, groq, grok, openrouter, ollama, bedrock)
        model: Model ID (e.g., 'gpt-4o', 'claude-sonnet-4-20250514', 'gemini-2.5-pro')
        messages: List of message dicts with 'role' and 'content' keys
        temperature: Sampling temperature (0.0-2.0, default 0.7)
        max_tokens: Maximum tokens to generate (optional)

    Returns:
        Model response content with usage statistics
    """
    client = LLMClient(provider=provider)
    msgs = [Message(role=m["role"], content=m["content"]) for m in messages]
    request = ChatRequest(model=model, messages=msgs, temperature=temperature, max_tokens=max_tokens)
    response = await client.chat_completion(request)

    return (
        f"{response.content}\n\n"
        f"---\n"
        f"Provider: {response.provider} | Model: {response.model}\n"
        f"Tokens: {response.usage.total_tokens} "
        f"(prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens})\n"
        f"Cost: ${response.usage.cost_usd:.6f}"
    )
```

---

### 3.4 Client Configuration

#### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "stratifyai": {
      "command": "python",
      "args": ["-m", "stratifyai.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "GOOGLE_API_KEY": "..."
      }
    }
  }
}
```

#### Claude Code (`.mcp.json` or project config)

```json
{
  "mcpServers": {
    "stratifyai": {
      "command": "python",
      "args": ["-m", "stratifyai.mcp_server"]
    }
  }
}
```

---

### 3.5 Implementation Phases

| Phase | Scope | Effort |
|-------|-------|--------|
| **Phase 1** | Core tools: `chat_completion`, `list_providers`, `list_models`, `get_model_info` | Low |
| **Phase 2** | Routing tools: `chat_with_routing`, `estimate_cost` | Low |
| **Phase 3** | Resources: catalog, providers, costs | Low |
| **Phase 4** | Cost tools: `get_cost_summary`, `validate_provider` | Low |
| **Phase 5** | Prompts: `compare_models`, `recommend_model`, `analyze_costs` | Low |
| **Phase 6** | Streamable HTTP transport, documentation, testing | Medium |

**Estimated total effort:** Low-Medium. FastMCP handles protocol complexity. Tools are thin wrappers around existing code.

---

### 3.6 Dependencies

Add to `pyproject.toml`:

```toml
[project.optional-dependencies]
mcp = ["mcp[cli]>=1.0.0"]
all = ["stratifyai[dev,cli,web,rag,mcp]"]
```

Add entry point:

```toml
[project.scripts]
stratifyai-mcp = "stratifyai.mcp_server:main"
```

---

### 3.7 Testing Strategy

- **Unit tests:** Mock `LLMClient` and test each tool/resource/prompt independently
- **Integration tests:** Use MCP Inspector (`fastmcp dev`) to test server interactively
- **Client tests:** Verify configuration works with Claude Desktop and Cursor

---

## Development Phases Summary

| Phase | Section | Description | Dependencies |
|-------|---------|-------------|-------------|
| **8.0** | Bug Fixes (P0-P1) | Critical + high-severity bugs | None |
| **8.1** | Bug Fixes (P2-P3) | Medium + low-severity bugs | 8.0 |
| **8.2** | Web UI Phase A-B | Scaffold + chat interface | 8.0 (needs fixed API) |
| **8.3** | Web UI Phase C-D | Config panel + catalog | 8.2 |
| **8.4** | Web UI Phase E-F | Polish + cutover | 8.3 |
| **8.5** | MCP Phase 1-3 | Core tools + resources | 8.0 (needs fixed API) |
| **8.6** | MCP Phase 4-6 | Cost tools + prompts + docs | 8.5 |

---

## Potential Challenges and Mitigations

| Challenge | Mitigation |
|-----------|-----------|
| Svelte 5 learning curve | Svelte syntax is closest to vanilla HTML/JS; extensive official tutorials available |
| SASS-only (no Tailwind) components take longer | Bits UI handles complex a11y; visual components are straightforward with tokens/mixins |
| MCP protocol changes | FastMCP 3.0 is stable; follow MCP changelog for breaking changes |
| Build step adds complexity | Vite config is ~15 lines; `npm run build` is one command; CI/CD handles automatically |
| Streaming chat with Svelte reactivity | Svelte 5 Runes (`$state`) are designed for this exact use case |

---

## Future Expansion

- **MCP Sampling:** Allow MCP clients to request StratifyAI to sample from its providers (MCP sampling capability)
- **MCP OAuth 2.1:** Secure MCP server with OAuth for multi-user deployments
- **Web UI:** Real-time cost visualization charts, conversation history persistence, multi-conversation tabs
- **Plugin system:** Third-party MCP tool providers that extend StratifyAI capabilities
