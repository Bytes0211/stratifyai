# PRD: MCP Client Engine

Version: 1.0
Date: 2026-04-03
Owner: StratifyAI Core Team
Status: Draft — depends on MCP Abstraction Layer (PRD-MCP-abstraction-layer.md)

---

## 1. Problem Statement

Today, StratifyAI is an MCP server — it exposes tools to external clients like Claude Desktop or Cursor. But StratifyAI itself cannot call other MCP servers. This means:

- Users who want StratifyAI to search the web (Tavily), access GitHub, or query a database must leave StratifyAI and use a separate MCP client.
- There is no way to compose MCP tools in a single StratifyAI chat session (e.g. "search the web then summarize with Claude").
- The Web UI cannot manage, monitor, or test external MCP servers.

The MCP Abstraction Layer (separate PRD) solves config generation. This PRD solves runtime execution — making StratifyAI a fully functional MCP client that spawns, manages, and calls external MCP servers.

---

## 2. Solution

Build an MCP Client Engine inside StratifyAI that:

1. **Spawns and manages MCP server processes** based on the user's config.
2. **Discovers tools/resources/prompts** from each connected server via the MCP handshake.
3. **Provides a unified tool registry** aggregating tools across all servers.
4. **Integrates with chat** so the LLM can call MCP tools during a conversation.
5. **Exposes management UI** in the Web SPA for server status, tool discovery, and inline testing.
6. **Enforces permissions** so users control what tools can do.

---

## 3. Architecture

### 3.1 System Diagram

```
User
  │
  ├── Web UI / CLI / API
  │     │
  │     ├── StratifyAI Core (LLMClient, Router, CostTracker)
  │     │
  │     ├── MCP Client Engine (NEW)
  │     │     ├── Server Manager — spawn/stop/restart stdio processes
  │     │     ├── Connection Pool — maintain ClientSession per server
  │     │     ├── Tool Registry — merged tool list from all servers
  │     │     ├── Tool Executor — route call to correct server
  │     │     └── Permission Layer — allow/deny/confirm per tool
  │     │
  │     └── MCP Server (existing — still serves Claude/Cursor)
  │
  └── External MCP Servers (spawned by Client Engine)
        ├── Tavily (stdio)
        ├── GitHub (stdio)
        ├── Filesystem (stdio)
        └── ... (any configured server)
```

### 3.2 Package Layout

```text
stratifyai/
  mcp_client/
    __init__.py
    engine.py           # MCPClientEngine — top-level orchestrator
    server_manager.py   # Spawn, stop, restart server processes
    connection.py       # ClientSession wrapper with reconnect logic
    tool_registry.py    # Aggregated tool/resource/prompt discovery
    executor.py         # Tool call routing and result formatting
    permissions.py      # Per-server and per-tool allow/deny/confirm
    config.py           # Load enabled servers from catalog/user config
```

### 3.3 Key Classes

```python
class MCPClientEngine:
    """Top-level orchestrator for MCP client functionality."""
    async def start() -> None           # Start all enabled servers
    async def stop() -> None            # Gracefully stop all servers
    async def call_tool(server: str, tool: str, args: dict) -> dict
    async def get_resource(server: str, uri: str) -> str
    def list_tools() -> list[ToolInfo]  # All tools across all servers
    def list_servers() -> list[ServerStatus]
    def get_server_status(server: str) -> ServerStatus

class ServerManager:
    """Manages MCP server process lifecycle."""
    async def spawn(server_id: str, command: str, args: list, env: dict) -> ClientSession
    async def stop(server_id: str) -> None
    async def restart(server_id: str) -> None
    def is_running(server_id: str) -> bool

class ToolRegistry:
    """Aggregated view of tools from all connected servers."""
    def register_server_tools(server_id: str, tools: list[Tool]) -> None
    def unregister_server(server_id: str) -> None
    def find_tool(server: str, name: str) -> Tool | None
    def list_all() -> list[ToolInfo]  # Namespaced as server.tool_name
```

---

## 4. Server Lifecycle

### 4.1 Startup Flow

1. Engine reads enabled servers from config (catalog + user customizations).
2. For each enabled server:
   a. Validate prerequisites (npx/node, docker, python as needed).
   b. Spawn subprocess with configured command, args, and env.
   c. Perform MCP initialization handshake.
   d. Discover tools/resources/prompts and register in tool registry.
   e. Mark server status as "connected".
3. Servers that fail to start are marked "error" with diagnostic message.

### 4.2 Health Monitoring

- Periodic ping (configurable interval, default 30s).
- On failure: mark server as "disconnected", attempt reconnect with backoff.
- Expose status via API endpoint and Web UI.

### 4.3 Shutdown

- Graceful `aclose()` on each ClientSession.
- Kill subprocess if graceful close times out (5s).
- Triggered on app shutdown, user action, or server removal.

---

## 5. Tool Execution

### 5.1 Call Flow

```
User/LLM requests: call_tool("tavily", "search", {"query": "latest GPT-5 benchmarks"})
  │
  ├── Permission check: is tavily.search allowed? Needs confirmation?
  ├── Route to ServerManager.get_session("tavily")
  ├── session.call_tool("search", {"query": "..."})
  ├── Parse result, format for LLM context
  └── Return to caller
```

### 5.2 Namespacing

Tools are namespaced as `{server_id}.{tool_name}` to avoid collisions:
- `tavily.search`
- `brave.search`
- `github.list_issues`
- `filesystem.read_file`

### 5.3 Error Handling

- Server not running → attempt auto-restart, fail with clear message if unsuccessful.
- Tool call timeout → configurable per-server (default 30s).
- Tool call error → propagate structured error to caller with server context.

---

## 6. Chat Integration

### 6.1 How It Works

During a chat session, the LLM can request tool calls. The flow:

1. User sends a message via Web UI, CLI, or API.
2. StratifyAI sends the message to the LLM (via existing LLMClient).
3. LLM response includes a tool_use request (if the model supports tool calling).
4. StratifyAI intercepts the tool call, routes it through MCPClientEngine.
5. Tool result is injected back into the conversation.
6. LLM generates the final response incorporating the tool result.
7. Web UI shows which server/tool was used for transparency.

### 6.2 Tool Availability in Chat

- User selects which MCP servers are "active" for the current session.
- Only tools from active servers are included in the LLM's tool definitions.
- Switching active servers mid-conversation is supported.

### 6.3 Fallback Behavior

- If a selected server is offline, show a warning and exclude its tools.
- If a tool call fails, return the error to the LLM so it can respond gracefully.
- If no MCP servers are active, chat works normally (no tool calling).

---

## 7. Permissions & Safety

### 7.1 Per-Server Controls

- **Enable/Disable** — toggle server on/off without removing config.
- **Auto-start** — whether server starts with the engine or only on demand.

### 7.2 Per-Tool Controls

- **Allow list** — only specified tools are callable (default: all allowed).
- **Deny list** — specific tools are blocked.
- **Confirm before execute** — prompt user for approval before calling (for destructive tools like `filesystem.delete_file`, `github.create_issue`).

### 7.3 Safety Defaults

Servers with write/side-effect tools default to confirm-before-execute:
- Filesystem: write, delete, move operations
- GitHub: create/close issues, merge PRs
- Slack: send messages
- Database: write/delete queries

Read-only tools (search, list, get) default to auto-approve.

---

## 8. Web UI Panels

### 8.1 Server Dashboard

- Card per connected server: name, status (connected/disconnected/error), transport, tool count.
- Actions: Start, Stop, Restart per server.
- Connection diagnostics: last handshake time, latency, error message if failed.

### 8.2 Tool Discovery Panel

- Expandable tree: Server > Tools/Resources/Prompts.
- Click a tool to see its input schema, description, and permissions.
- Inline test: JSON editor for input, execute button, response viewer.
- Save sample requests as presets.

### 8.3 Chat Integration Panel

- In chat settings sidebar: checkboxes for active MCP servers.
- In chat messages: badge showing which tool was called and from which server.
- Expandable tool result detail (input args, output, latency).

### 8.4 Permission Manager

- Table: Server | Tool | Permission (Allow/Deny/Confirm).
- Bulk actions: "Allow all read-only", "Confirm all write tools".
- Per-server override toggle.

---

## 9. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mcp-client/servers` | GET | List all servers with status |
| `/api/mcp-client/servers/{id}/start` | POST | Start a server |
| `/api/mcp-client/servers/{id}/stop` | POST | Stop a server |
| `/api/mcp-client/servers/{id}/restart` | POST | Restart a server |
| `/api/mcp-client/tools` | GET | List all tools across all servers |
| `/api/mcp-client/tools/{server}/{tool}` | POST | Execute a tool call |
| `/api/mcp-client/resources/{server}/{uri}` | GET | Fetch a resource |
| `/api/mcp-client/permissions` | GET/PUT | Read/update permission config |
| `/api/mcp-client/health` | GET | Health summary for all servers |

---

## 10. Configuration

The MCP Client Engine reads from the same catalog and user config that the Abstraction Layer manages. No separate config needed.

```json
{
  "mcp_client": {
    "auto_start": true,
    "health_check_interval_seconds": 30,
    "default_tool_timeout_seconds": 30,
    "servers": {
      "tavily": {
        "enabled": true,
        "auto_start": true,
        "permissions": {
          "default": "allow",
          "confirm": ["tavily_extract"]
        }
      },
      "github": {
        "enabled": true,
        "auto_start": false,
        "permissions": {
          "default": "confirm",
          "allow": ["list_issues", "get_repo", "search_code"]
        }
      }
    }
  }
}
```

---

## 11. Implementation Phases

### Phase 1: Client Engine Core
- `MCPClientEngine`, `ServerManager`, `connection.py`
- Spawn stdio servers, perform handshake, discover tools
- `call_tool()` and `get_resource()` working end-to-end
- Unit tests with mock MCP servers

### Phase 2: Tool Registry & Namespacing
- `ToolRegistry` with server-namespaced tool aggregation
- Handle server connect/disconnect (register/unregister)
- `list_tools()` API

### Phase 3: Chat Integration
- Wire tool registry into chat flow (LLMClient tool_use support)
- Tool result injection into conversation context
- Active server selection per chat session

### Phase 4: Permissions & Safety
- `permissions.py` with allow/deny/confirm logic
- Safety defaults for write/destructive tools
- Confirm-before-execute flow in Web UI and CLI

### Phase 5: Web UI Panels
- Server Dashboard with status and actions
- Tool Discovery Panel with inline testing
- Chat integration badges and tool result display
- Permission Manager table

### Phase 6: API Endpoints & Diagnostics
- REST endpoints for server management and tool calls
- Health monitoring with periodic ping
- Connection diagnostics and error reporting

### Phase 7: Tests & Documentation
- Unit tests for engine, registry, executor, permissions
- Integration tests with real MCP server (e.g. filesystem server)
- Web UI component tests
- User documentation and troubleshooting guide

---

## 12. Dependencies

- `mcp` Python SDK (already installed) — provides `ClientSession`, `StdioServerParameters`
- MCP Abstraction Layer PRD — provides catalog and user config
- Existing StratifyAI chat flow — provides LLMClient integration point

---

## 13. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Subprocess management complexity (zombie processes, leaked file descriptors) | Use `asyncio.create_subprocess_exec` with explicit cleanup on shutdown; process group kill on timeout |
| Tool call latency adds to chat response time | Timeout per tool call; show streaming progress indicator; run tool calls in parallel where possible |
| MCP SDK client API changes in v2 | Isolate SDK usage in `connection.py`; same pin strategy as server (`>=1.25,<2`) |
| Security: malicious tool output injected into LLM context | Sanitize tool output; enforce max output size; permission layer gates execution |
| Resource consumption from many concurrent servers | Limit max concurrent servers (configurable, default 10); lazy start on demand |

---

## 14. Relationship to Other PRDs

| PRD | Relationship |
|-----|-------------|
| PRD-MCP-implemenation.md | StratifyAI as MCP server — unchanged, both can run simultaneously |
| PRD-MCP-abstraction-layer.md | Provides catalog and config management used by the client engine |
| This PRD | StratifyAI as MCP client — spawns and calls external servers |

The three PRDs are complementary:
- **Server PRD:** Other tools call us
- **Abstraction Layer PRD:** Users configure which servers exist
- **Client Engine PRD:** We call other tools
