<script lang="ts">
  import { onMount } from 'svelte';
  import {
    configureMcp,
    getMcpCatalog,
    getMcpClients,
    getMcpStatus,
  } from '$lib/api/client';
  import type {
    McpCatalogResponse,
    McpClientInfo,
    McpConfigureRequest,
    McpConfigureResponse,
    McpStatusResponse,
  } from '$lib/api/types';
  import Button from '../shared/Button.svelte';
  import LoadingSpinner from '../shared/LoadingSpinner.svelte';
  import MCPToolTester from './MCPToolTester.svelte';
  import {
    AlertCircle,
    CheckCircle2,
    Copy,
    Download,
    PlugZap,
    RefreshCw,
    Server,
    Settings2,
  } from 'lucide-svelte';

  let catalog: McpCatalogResponse | null = null;
  let clients: McpClientInfo[] = [];
  let selectedClient: McpConfigureRequest['client'] = 'cursor';
  let projectRoot = '';
  let selectedCategory = 'all';
  let searchQuery = '';
  let selectedServerIds: string[] = [];
  let envValues: Record<string, string> = {};
  let argValues: Record<string, string> = {};
  let statusData: McpStatusResponse | null = null;
  let preview: McpConfigureResponse | null = null;
  let loading = true;
  let actionLoading = false;
  let error: string | null = null;
  let statusMessage = '';
  let copyMessage = '';

  onMount(() => {
    void initialize();
  });

  async function initialize() {
    try {
      loading = true;
      error = null;
      const [catalogData, clientData] = await Promise.all([
        getMcpCatalog(),
        getMcpClients(projectRoot || undefined),
      ]);
      catalog = catalogData;
      clients = clientData.clients;
      if (clients.length > 0 && !clients.some((item) => item.id === selectedClient)) {
        selectedClient = clients[0].id;
      }
      await refreshStatus();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load MCP management data';
    } finally {
      loading = false;
    }
  }

  async function refreshStatus() {
    try {
      statusData = await getMcpStatus(selectedClient, projectRoot || undefined);
    } catch (err) {
      statusData = null;
      error = err instanceof Error ? err.message : 'Failed to load MCP client status';
    }
  }

  function toggleServer(serverId: string) {
    if (selectedServerIds.includes(serverId)) {
      selectedServerIds = selectedServerIds.filter((id) => id !== serverId);
    } else {
      selectedServerIds = [...selectedServerIds, serverId];
    }
    statusMessage = '';
    copyMessage = '';
  }

  function updateEnvValue(name: string, value: string) {
    envValues = { ...envValues, [name]: value };
  }

  function updateArgValue(serverId: string, name: string, value: string) {
    argValues = { ...argValues, [`${serverId}.${name}`]: value };
  }

  async function generateConfig(apply = false) {
    if (selectedServerIds.length === 0) {
      statusMessage = 'Select at least one MCP server to continue.';
      return;
    }

    try {
      actionLoading = true;
      error = null;
      copyMessage = '';
      preview = await configureMcp({
        client: selectedClient,
        server_ids: selectedServerIds,
        env_values: envValues,
        arg_values: argValues,
        project_root: projectRoot || undefined,
        apply,
      });
      statusMessage = preview.applied
        ? `Configuration applied${preview.path ? ` to ${preview.path}` : ''}.`
        : selectedClient === 'claude-code'
          ? 'Commands generated for Claude Code.'
          : 'Preview updated.';

      if (apply) {
        await refreshStatus();
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to generate MCP configuration';
    } finally {
      actionLoading = false;
    }
  }

  async function copyPreview() {
    if (!renderedPreview) {
      copyMessage = 'Nothing to copy yet.';
      return;
    }

    try {
      await navigator.clipboard.writeText(renderedPreview);
      copyMessage = 'Copied to clipboard.';
    } catch {
      copyMessage = 'Clipboard copy failed.';
    }
  }

  function downloadPreview() {
    if (!renderedPreview) {
      copyMessage = 'Nothing to download yet.';
      return;
    }

    const mimeType = selectedClient === 'claude-code' ? 'text/plain;charset=utf-8' : 'application/json;charset=utf-8';
    const blob = new Blob([renderedPreview], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = selectedClient === 'claude-code' ? 'claude-code-mcp-commands.txt' : `${selectedClient}-mcp-config.json`;
    link.click();
    URL.revokeObjectURL(url);
    copyMessage = 'Download started.';
  }

  function isConfigured(serverId: string): boolean {
    return Boolean(statusData?.configured?.[serverId]);
  }

  $: categories = catalog
    ? ['all', ...Array.from(new Set(catalog.servers.map((server) => server.category))).sort()]
    : ['all'];

  $: filteredServers = (catalog?.servers ?? [])
    .filter((server) => selectedCategory === 'all' || server.category === selectedCategory)
    .filter((server) => {
      const q = searchQuery.trim().toLowerCase();
      if (!q) return true;
      return (
        server.name.toLowerCase().includes(q) ||
        server.id.toLowerCase().includes(q) ||
        server.description.toLowerCase().includes(q) ||
        server.tags.some((tag) => tag.toLowerCase().includes(q))
      );
    })
    .sort((a, b) => a.name.localeCompare(b.name));

  $: selectedClientInfo = clients.find((item) => item.id === selectedClient) ?? null;
  $: renderedPreview = preview
    ? preview.commands.length > 0
      ? preview.commands.join('\n')
      : JSON.stringify(preview.config ?? {}, null, 2)
    : '';
</script>

<div class="mcp-page">
  <div class="page-header">
    <div>
      <h1>MCP Servers</h1>
      <p>Browse, configure, preview, and apply curated MCP integrations for supported clients.</p>
    </div>
    <div class="header-actions">
      <Button variant="secondary" size="sm" on:click={refreshStatus}>
        <RefreshCw size={16} />
        Refresh status
      </Button>
    </div>
  </div>

  {#if loading}
    <div class="loading-state card">
      <LoadingSpinner size="lg" />
      <span>Loading MCP catalog and client status...</span>
    </div>
  {:else}
    <div class="controls-grid">
      <section class="card control-panel">
        <div class="section-title">
          <Settings2 size={18} />
          <h2>Target Client</h2>
        </div>

        <label>
          <span>Client</span>
          <select bind:value={selectedClient} on:change={() => refreshStatus()}>
            {#each clients as client}
              <option value={client.id}>{client.label}</option>
            {/each}
          </select>
        </label>

        <label>
          <span>Project root (optional)</span>
          <input
            type="text"
            bind:value={projectRoot}
            placeholder="Defaults to the server working directory"
          />
        </label>

        <div class="helper-row">
          <span class="helper-label">Apply support</span>
          <strong>{selectedClientInfo?.supports_apply ? 'Yes' : 'Commands only'}</strong>
        </div>

        <div class="helper-row">
          <span class="helper-label">Config path</span>
          <code>{selectedClientInfo?.config_path ?? 'Managed via CLI commands'}</code>
        </div>
      </section>

      <section class="card status-panel">
        <div class="section-title">
          <Server size={18} />
          <h2>Current Status</h2>
        </div>

        <div class="status-metrics">
          <div>
            <strong>{statusData?.count ?? 0}</strong>
            <span>configured</span>
          </div>
          <div>
            <strong>{selectedServerIds.length}</strong>
            <span>selected</span>
          </div>
        </div>

        <p class="path-text">{statusData?.path ?? 'No config file path resolved for this client.'}</p>

        {#if statusData && statusData.count > 0}
          <div class="configured-list">
            {#each Object.keys(statusData.configured) as serverId}
              <span class="chip configured">{serverId}</span>
            {/each}
          </div>
        {:else}
          <p class="muted">No configured servers detected yet.</p>
        {/if}
      </section>
    </div>

    <section class="card filter-panel">
      <div class="section-title">
        <PlugZap size={18} />
        <h2>Catalog Browser</h2>
      </div>

      <div class="filter-row">
        <input type="text" bind:value={searchQuery} placeholder="Search by name, id, or tag" />
        <select bind:value={selectedCategory}>
          {#each categories as category}
            <option value={category}>{category === 'all' ? 'All categories' : category}</option>
          {/each}
        </select>
      </div>
    </section>

    {#if error}
      <div class="error-banner card">
        <AlertCircle size={18} />
        <span>{error}</span>
      </div>
    {/if}

    <div class="content-grid">
      <section class="catalog-grid">
        {#each filteredServers as server (server.id)}
          <article class:selected={selectedServerIds.includes(server.id)} class:configured={isConfigured(server.id)} class="server-card card">
            <div class="server-card__header">
              <div>
                <h3>{server.name}</h3>
                <p>{server.description}</p>
              </div>
              <button class:selected={selectedServerIds.includes(server.id)} class="toggle-button" on:click={() => toggleServer(server.id)}>
                {selectedServerIds.includes(server.id) ? 'Selected' : 'Select'}
              </button>
            </div>

            <div class="server-meta">
              <span class="chip">{server.category}</span>
              <span class="chip">{server.install_method}</span>
              {#if isConfigured(server.id)}
                <span class="chip configured">Configured</span>
              {/if}
            </div>

            {#if server.website}
              <a class="website-link" href={server.website} target="_blank" rel="noreferrer">Docs ↗</a>
            {/if}

            {#if selectedServerIds.includes(server.id) && (server.env_vars.length > 0 || server.user_args.length > 0)}
              <div class="server-form">
                {#each server.env_vars as envVar}
                  <label>
                    <span>{envVar.name}{envVar.required ? ' *' : ''}</span>
                    <input
                      type={envVar.secret ? 'password' : 'text'}
                      value={envValues[envVar.name] ?? ''}
                      placeholder={envVar.description || envVar.name}
                      on:input={(event) => updateEnvValue(envVar.name, (event.currentTarget as HTMLInputElement).value)}
                    />
                  </label>
                {/each}

                {#each server.user_args as userArg}
                  <label>
                    <span>{userArg.name}{userArg.required ? ' *' : ''}</span>
                    <input
                      type="text"
                      value={argValues[`${server.id}.${userArg.name}`] ?? userArg.example ?? ''}
                      placeholder={userArg.description || userArg.name}
                      on:input={(event) => updateArgValue(server.id, userArg.name, (event.currentTarget as HTMLInputElement).value)}
                    />
                  </label>
                {/each}
              </div>
            {/if}
          </article>
        {/each}
      </section>

      <aside class="preview-panel card">
        <div class="section-title">
          <CheckCircle2 size={18} />
          <h2>Preview & Apply</h2>
        </div>

        <div class="action-row">
          <Button variant="primary" on:click={() => generateConfig(false)} loading={actionLoading}>
            Preview config
          </Button>
          <Button
            variant="secondary"
            on:click={() => generateConfig(true)}
            disabled={actionLoading || !selectedClientInfo?.supports_apply}
          >
            {selectedClientInfo?.supports_apply ? 'Apply config' : 'Commands only'}
          </Button>
        </div>

        <div class="action-row secondary-actions">
          <Button variant="ghost" size="sm" on:click={copyPreview}>
            <Copy size={14} />
            Copy
          </Button>
          <Button variant="ghost" size="sm" on:click={downloadPreview}>
            <Download size={14} />
            Download
          </Button>
        </div>

        {#if statusMessage}
          <p class="success-text">{statusMessage}</p>
        {/if}
        {#if copyMessage}
          <p class="muted">{copyMessage}</p>
        {/if}

        {#if preview?.warnings?.length}
          <div class="warning-box">
            {#each preview.warnings as warning}
              <p>{warning}</p>
            {/each}
          </div>
        {/if}

        <pre class="preview-output">{renderedPreview || 'Select one or more servers, then click “Preview config”.'}</pre>
      </aside>
    </div>

    <MCPToolTester />
  {/if}
</div>

<style lang="scss">
  @use '../../../styles/tokens' as *;
  @use '../../../styles/mixins' as *;

  .mcp-page {
    display: flex;
    flex-direction: column;
    gap: $space-4;
    max-width: 1440px;
    margin: 0 auto;
    padding: $space-4;

    @include lg {
      padding: $space-6;
    }
  }

  .card {
    background: var(--bg-surface);
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-xl;
    padding: $space-4;
    box-shadow: $shadow-sm;
  }

  .page-header,
  .section-title,
  .helper-row,
  .filter-row,
  .action-row,
  .server-card__header,
  .status-metrics {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $space-3;
  }

  .page-header {
    flex-wrap: wrap;

    h1 {
      margin: 0 0 $space-1;
      font-size: $text-2xl;
      color: var(--text-primary);
    }

    p {
      margin: 0;
      color: var(--text-secondary);
    }
  }

  .section-title {
    justify-content: flex-start;
    margin-bottom: $space-3;

    h2 {
      margin: 0;
      font-size: $text-lg;
      color: var(--text-primary);
    }
  }

  .controls-grid,
  .content-grid {
    display: grid;
    gap: $space-4;
  }

  .controls-grid {
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }

  .content-grid {
    grid-template-columns: minmax(0, 2fr) minmax(320px, 1fr);

    @media (max-width: 1100px) {
      grid-template-columns: 1fr;
    }
  }

  .catalog-grid {
    display: grid;
    gap: $space-4;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  }

  .server-card {
    display: flex;
    flex-direction: column;
    gap: $space-3;

    &.selected {
      border-color: var(--accent);
    }

    &.configured {
      box-shadow: inset 0 0 0 1px rgba(16, 185, 129, 0.4);
    }

    h3 {
      margin: 0;
      color: var(--text-primary);
    }

    p {
      margin: $space-1 0 0;
      color: var(--text-secondary);
      font-size: $text-sm;
    }
  }

  .toggle-button {
    border: 1px solid var(--bg-hover);
    background: var(--bg-elevated);
    color: var(--text-primary);
    border-radius: $radius-lg;
    padding: $space-2 $space-3;
    font-size: $text-sm;
    cursor: pointer;

    &.selected {
      background: var(--accent);
      color: #0f172a;
      border-color: transparent;
    }
  }

  .server-meta,
  .configured-list {
    display: flex;
    flex-wrap: wrap;
    gap: $space-2;
  }

  .chip {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: $space-1 $space-2;
    background: var(--bg-elevated);
    color: var(--text-secondary);
    font-size: $text-xs;
    font-weight: $font-medium;

    &.configured {
      background: rgba(16, 185, 129, 0.14);
      color: #10b981;
    }
  }

  .website-link {
    font-size: $text-sm;
    color: var(--accent);
    text-decoration: none;
  }

  .server-form,
  .control-panel {
    display: flex;
    flex-direction: column;
    gap: $space-3;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: $space-1;

    span {
      font-size: $text-sm;
      color: var(--text-secondary);
    }
  }

  input,
  select {
    width: 100%;
    border: 1px solid var(--bg-hover);
    background: var(--bg-base);
    color: var(--text-primary);
    border-radius: $radius-lg;
    padding: $space-2 $space-3;
    font-size: $text-sm;
  }

  .helper-row {
    align-items: flex-start;

    strong,
    code {
      color: var(--text-primary);
      word-break: break-all;
    }
  }

  .helper-label,
  .muted,
  .path-text {
    color: var(--text-secondary);
    font-size: $text-sm;
  }

  .status-metrics {
    justify-content: flex-start;
    gap: $space-6;
    margin-bottom: $space-3;

    div {
      display: flex;
      flex-direction: column;
      gap: $space-1;
    }

    strong {
      font-size: $text-xl;
      color: var(--text-primary);
    }

    span {
      color: var(--text-secondary);
      font-size: $text-sm;
    }
  }

  .filter-row,
  .action-row {
    flex-wrap: wrap;
  }

  .secondary-actions {
    justify-content: flex-start;
  }

  .preview-panel {
    display: flex;
    flex-direction: column;
    gap: $space-3;
    min-height: 420px;
  }

  .preview-output {
    margin: 0;
    flex: 1;
    min-height: 280px;
    padding: $space-3;
    border-radius: $radius-lg;
    border: 1px solid var(--bg-elevated);
    background: var(--bg-base);
    color: var(--text-primary);
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: $text-xs;
    line-height: 1.5;
  }

  .warning-box,
  .error-banner {
    display: flex;
    flex-direction: column;
    gap: $space-2;
    border-left: 3px solid #f59e0b;
    background: rgba(245, 158, 11, 0.08);
  }

  .error-banner {
    flex-direction: row;
    align-items: center;
    border-left-color: #ef4444;
    background: rgba(239, 68, 68, 0.08);
    color: #ef4444;
  }

  .success-text {
    color: #10b981;
    font-size: $text-sm;
    margin: 0;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: $space-3;
    min-height: 280px;
    color: var(--text-secondary);
  }
</style>
