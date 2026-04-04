# PRD: MCP Abstraction Layer

Version: 1.0
Date: 2026-04-03
Owner: StratifyAI Core Team
Status: Draft

---

## 1. Problem Statement

Configuring MCP servers is tedious and error-prone. Users must:
- Discover available MCP servers across npm, PyPI, Docker, and hosted registries
- Manually research install commands, required env vars, and config JSON format
- Hand-edit client-specific config files (different paths per OS and per client)
- Repeat this for every new MCP server they want to add

This creates a barrier to adoption, especially for non-developer users of AI assistants.

---

## 2. Solution

Build an MCP Abstraction Layer that provides:

1. **Curated MCP Server Catalog** — a JSON registry of popular MCP servers with install commands, env var requirements, and config templates.
2. **CLI Wizard** (`stratifyai mcp setup`) — interactive setup that walks users through selecting servers, entering credentials, and writing the correct config file.
3. **Web UI** — a Svelte tab in the existing SPA where users browse, toggle, and configure MCP servers visually.

Both interfaces read from the same catalog and produce the same output: a valid MCP client config file.

---

## 3. User Experience

### 3.1 CLI Flow

```
$ stratifyai mcp setup

? Which MCP client are you using?
  > Claude Desktop
    Claude Code
    Cursor
    VS Code (Copilot Chat)

? Select MCP servers to enable:
  ── Search ──
  [x] Tavily (web search with AI)
  [ ] Brave Search (web search)
  [ ] Perplexity (AI-powered search)
  [ ] Exa (semantic code search)
  ── Developer Tools ──
  [x] GitHub (repos, PRs, issues)
  [ ] Git (local git operations)
  [x] Context7 (code documentation)
  ── Productivity ──
  [ ] Slack (messaging)
  [ ] Atlassian (Jira, Confluence)
  [ ] Stripe (payments)
  ── Data ──
  [ ] PostgreSQL (database)
  [ ] SQLite (database)
  [ ] Supabase (backend services)
  ── Utilities ──
  [x] Filesystem (local file access)
  [ ] Fetch (web content to markdown)
  [x] Memory (persistent knowledge graph)
  [ ] Sequential Thinking (structured reasoning)
  ── Automation ──
  [ ] Playwright (browser automation)
  ── Design ──
  [ ] Figma (design files)
  ── Cloud ──
  [ ] Cloudflare (deploy & manage)
  ── LLM ──
  [x] StratifyAI (multi-provider LLM routing) [always included]

? Tavily API key: tvly-...
? GitHub personal access token: ghp-...
? Context7 API key: ctx7-...
? Filesystem — allowed directories (comma-separated): /home/user/projects,/tmp

✓ Config written to ~/Library/Application Support/Claude/claude_desktop_config.json
  3 servers require npx (Node.js). Ensure Node.js is installed.
  Restart Claude Desktop to activate 6 MCP servers.
```

### 3.2 Additional CLI Commands

```bash
# Interactive setup wizard
stratifyai mcp setup

# List available servers from catalog
stratifyai mcp list

# List currently configured servers
stratifyai mcp status

# Add a single server
stratifyai mcp add tavily --key tvly-...

# Remove a server
stratifyai mcp remove tavily

# Generate config without writing (preview)
stratifyai mcp setup --dry-run

# Update catalog to latest version
stratifyai mcp catalog-update
```

### 3.3 Web UI Flow

New "MCP Servers" tab in the Svelte SPA:

1. **Browse** — card grid of available MCP servers, grouped by category, with description, icon, and toggle switch.
2. **Configure** — clicking a toggled server expands a form for required env vars / args.
3. **Client Select** — dropdown to choose target client (Claude Desktop, Cursor, etc.).
4. **Export** — "Generate Config" button produces the JSON block. "Copy to Clipboard" or "Download" options. Optionally "Apply" writes directly to the client config path.
5. **Status** — shows which servers are currently enabled in the detected config file.

---

## 4. MCP Server Catalog

### 4.1 Catalog Format

```json
{
  "version": "1.0",
  "updated": "2026-04-03",
  "servers": [
    {
      "id": "tavily",
      "name": "Tavily",
      "description": "Real-time web search with AI-powered results",
      "category": "search",
      "website": "https://tavily.com",
      "install_method": "npx",
      "command": "npx",
      "args": ["-y", "tavily-mcp@latest"],
      "env_vars": [
        {
          "name": "TAVILY_API_KEY",
          "description": "Tavily API key",
          "required": true,
          "signup_url": "https://app.tavily.com/sign-up"
        }
      ],
      "user_args": [],
      "tags": ["search", "web", "ai"]
    }
  ]
}
```

### 4.2 Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (lowercase, kebab-case) |
| `name` | string | Display name |
| `description` | string | One-line description |
| `category` | string | Category: search, developer, productivity, data, utilities, automation, design, cloud, llm |
| `website` | string | Homepage or docs URL |
| `install_method` | string | npx, pip, docker, remote |
| `command` | string | Command to run the server |
| `args` | list[string] | Static arguments |
| `env_vars` | list[EnvVar] | Required/optional environment variables |
| `user_args` | list[UserArg] | User-provided arguments (e.g. filesystem paths) |
| `tags` | list[string] | Searchable tags |

### 4.3 Initial Catalog (20 servers)

| ID | Name | Category | Install | Requires Key |
|----|------|----------|---------|--------------|
| `stratifyai` | StratifyAI | llm | pip | Yes (provider keys) |
| `tavily` | Tavily | search | npx | Yes |
| `brave-search` | Brave Search | search | npx | Yes |
| `perplexity` | Perplexity | search | npx | Yes |
| `exa` | Exa | search | npx | Yes |
| `github` | GitHub | developer | npx | Yes |
| `git` | Git | developer | npx | No |
| `context7` | Context7 | developer | npx | Yes |
| `filesystem` | Filesystem | utilities | npx | No (paths as args) |
| `fetch` | Fetch | utilities | npx | No |
| `memory` | Memory | utilities | npx | No |
| `sequential-thinking` | Sequential Thinking | utilities | npx | No |
| `playwright` | Playwright | automation | npx | No |
| `slack` | Slack | productivity | npx | Yes |
| `atlassian` | Atlassian | productivity | remote | Yes (OAuth) |
| `stripe` | Stripe | productivity | npx | Yes |
| `postgresql` | PostgreSQL | data | npx | Yes (connection string) |
| `sqlite` | SQLite | data | npx | No (path as arg) |
| `supabase` | Supabase | data | npx | Yes |
| `figma` | Figma | design | npx | Yes |
| `cloudflare` | Cloudflare | cloud | npx | Yes |

---

## 5. Client Config Paths

### 5.1 Known Client Config Locations

| Client | macOS | Linux | Windows |
|--------|-------|-------|---------|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` | `~/.config/Claude/claude_desktop_config.json` | `%APPDATA%\Claude\claude_desktop_config.json` |
| Claude Code | `claude mcp add` CLI command | Same | Same |
| Cursor | `{project}/.cursor/mcp.json` | Same | Same |
| VS Code | `{project}/.vscode/settings.json` (under `mcp.servers`) | Same | Same |

### 5.2 Config Merge Strategy

When writing config:
1. Read existing config file (if present).
2. Merge `mcpServers` — add new entries, preserve existing ones.
3. Prompt before overwriting an existing server entry.
4. Back up original file to `{filename}.backup` before writing.

---

## 6. Technical Design

### 6.1 Package Layout

```text
stratifyai/
  mcp_catalog/
    __init__.py
    catalog.json          # Curated MCP server registry
    manager.py            # Catalog CRUD, config generation, client detection
    schemas.py            # Pydantic models for catalog entries
```

### 6.2 CLI Integration

Add to `cli/stratifyai_cli.py`:
- `mcp` command group with subcommands: `setup`, `list`, `status`, `add`, `remove`, `catalog-update`
- Interactive prompts via `rich` (checkboxes, text input, confirmation)

### 6.3 API Endpoints (for Web UI)

Add to `api/main.py`:
- `GET /api/mcp/catalog` — return full catalog
- `GET /api/mcp/status` — return currently configured servers (reads client config)
- `POST /api/mcp/configure` — accept selected servers + credentials, return or write config
- `GET /api/mcp/clients` — return supported clients with detected config paths

### 6.4 Web UI

New Svelte tab "MCP Servers" in the existing SPA:
- Server browser with category filtering and search
- Toggle switches with credential forms
- Config preview and export

---

## 7. Security

- API keys entered during setup are written to client config files only (not stored by StratifyAI).
- Keys are never logged or sent to StratifyAI servers.
- Config file backups preserve existing secrets.
- Catalog is local — no telemetry or external calls during setup.

---

## 8. Implementation Phases

### Phase 1: Catalog + CLI Core
- Create `mcp_catalog/` package with catalog.json and manager.py
- Implement `stratifyai mcp list` and `stratifyai mcp setup` (wizard)
- Implement config generation for all 4 clients
- Implement config file read/merge/write with backup
- Prerequisite validation (warn if Node.js/npx or Docker not installed for selected servers)
- Remote catalog update: `stratifyai mcp catalog-update` fetches latest from GitHub raw URL

### Phase 2: Additional CLI Commands
- `stratifyai mcp status` — show configured servers
- `stratifyai mcp add <server>` — add single catalog server
- `stratifyai mcp add-custom --command ... --env ...` — add custom user-defined server
- `stratifyai mcp remove <server>` — remove server
- `stratifyai mcp setup --dry-run` — preview without writing

### Phase 3: Web UI
- API endpoints for catalog, status, configure, clients
- Svelte "MCP Servers" tab with browse, toggle, configure
- Context-aware Apply/Export: detect local (localhost origin) vs remote; show Apply + Export for local, Export-only for remote
- Config preview, clipboard copy, and download

### Phase 4: Inline Tool Tester
- Add "Test MCP" panel to Web UI that connects to local `stratifyai-mcp` server
- Tool browser: list all registered tools with input schemas
- JSON input editor with schema-driven field hints
- Execute tool call and display JSON response
- Save sample requests as reusable presets (stored in localStorage)
- API endpoint: `POST /api/mcp/test-tool` — proxies tool call to local MCP server

### Phase 5: Polish
- Server health check (can the configured server actually start?)
- Custom server management in Web UI
- Tests and documentation

---

## 9. Acceptance Criteria

- [ ] User can run `stratifyai mcp setup` and have a working Claude Desktop config in under 3 minutes.
- [ ] Existing config entries are preserved when adding new servers.
- [ ] Config backup is created before any write.
- [ ] Web UI allows browse, toggle, configure, and export for all catalog servers.
- [ ] All 20 catalog servers have accurate install commands and env var requirements.
- [ ] No API keys are logged or persisted outside the client config file.
- [ ] Inline tool tester can call any registered `stratifyai-mcp` tool and display the result.

---

## 10. Resolved Design Decisions

| # | Question | Decision | Rationale |
|---|----------|----------|-----------|
| 1 | Custom/user-added servers? | **Yes** — `stratifyai mcp add-custom --command ... --env ...` | Power users need to add servers not in the catalog (internal tools, niche servers). |
| 2 | Remote catalog updates? | **Yes** — `stratifyai mcp catalog-update` fetches latest catalog.json from GitHub raw URL | MCP ecosystem moves fast; users shouldn't need to upgrade the full package for new servers. |
| 3 | Prerequisite validation? | **Yes** — check Node.js/npx and Docker before writing config | Prevents confusing "command not found" errors at runtime. Warn and continue (don't block). |
| 4 | Web UI Apply vs Export? | **Both, context-aware** — detect local vs remote. If request origin is localhost, show Apply + Export. If remote, show Export only (copy/download). | Apply is the best UX for local dev (common case). Browser is sandboxed and cannot write to a remote user's filesystem, so Export is the only option for remote. Degrades gracefully. |
