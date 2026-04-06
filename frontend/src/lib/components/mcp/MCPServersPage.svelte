<script lang="ts">
  import { onMount } from 'svelte';
  import {
    configureMcp,
    getMcpCatalog,
    getMcpClientPermissions,
    getMcpClientServers,
    getMcpClientTools,
    getMcpClients,
    getMcpStatus,
    restartMcpClientServer,
    removeMcpClientTool,
    resetMcpConfig,
    startMcpClientServer,
    stopMcpClientServer,
    updateMcpClientPermissions,
  } from '$lib/api/client';
  import type {
    McpCatalogResponse,
    McpClientInfo,
    McpClientPermissionsResponse,
    McpClientServerInfo,
    McpClientToolInfo,
    McpConfigureRequest,
    McpConfigureResponse,
    McpPermissionRules,
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
    Play,
    PlugZap,
    Power,
    RefreshCw,
    Server,
    Settings2,
    Shield,
    Square,
    Trash2,
    Wrench,
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
  let runtimeServers: McpClientServerInfo[] = [];
  let runtimeTools: McpClientToolInfo[] = [];
  let permissionData: McpClientPermissionsResponse | null = null;
  let selectedRuntimeTool = '';
  let permissionDrafts: Record<string, {
    enabled: boolean;
    auto_start: boolean;
    allowInput: string;
    denyInput: string;
    confirmInput: string;
  }> = {};
  let preview: McpConfigureResponse | null = null;
  let loading = true;
  let dashboardLoading = false;
  let actionLoading = false;
  let runtimeActionLoading = '';
  let permissionsSaving = false;
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
      await refreshRuntimePanels();
    } catch (err) {
      statusData = null;
      error = err instanceof Error ? err.message : 'Failed to load MCP client status';
    }
  }

  function joinRules(values: string[] = []): string {
    return values.join(', ');
  }

  function splitRules(value: string): string[] {
    return value
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function initializePermissionDrafts(response: McpClientPermissionsResponse) {
    permissionDrafts = Object.fromEntries(
      Object.entries(response.servers).map(([serverId, config]) => [
        serverId,
        {
          enabled: config.enabled,
          auto_start: config.auto_start,
          allowInput: joinRules(config.permissions.allow),
          denyInput: joinRules(config.permissions.deny),
          confirmInput: joinRules(config.permissions.confirm),
        },
      ])
    );
  }

  async function refreshRuntimePanels() {
    try {
      dashboardLoading = true;
      const [serversResponse, toolsResponse, permissionsResponse] = await Promise.all([
        getMcpClientServers(true),
        getMcpClientTools(true),
        getMcpClientPermissions(selectedClient, projectRoot || undefined),
      ]);
      runtimeServers = serversResponse.servers;
      runtimeTools = toolsResponse.tools;
      permissionData = permissionsResponse;
      initializePermissionDrafts(permissionsResponse);

      if (!runtimeTools.some((tool) => tool.namespace === selectedRuntimeTool)) {
        selectedRuntimeTool = runtimeTools[0]?.namespace ?? '';
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load live MCP client data';
      // Preserve the last successful dashboard state so configured MCP servers
      // do not disappear from the UI during a transient refresh failure.
    } finally {
      dashboardLoading = false;
    }
  }

  async function runServerAction(serverId: string, action: 'start' | 'stop' | 'restart') {
    try {
      runtimeActionLoading = `${serverId}:${action}`;
      error = null;
      if (action === 'start') {
        await startMcpClientServer(serverId);
      } else if (action === 'stop') {
        await stopMcpClientServer(serverId);
      } else {
        await restartMcpClientServer(serverId);
      }
      const verb = action === 'stop' ? 'stopped' : `${action}ed`;
      statusMessage = `${serverId} ${verb} successfully.`;
      await refreshRuntimePanels();
    } catch (err) {
      error = err instanceof Error ? err.message : `Failed to ${action} ${serverId}`;
    } finally {
      runtimeActionLoading = '';
    }
  }

  async function removeServer(serverId: string) {
    if (typeof window !== 'undefined' && !window.confirm(`Remove server "${serverId}" from the live dashboard? It will reappear on next refresh if still configured.`)) {
      return;
    }
    try {
      runtimeActionLoading = `${serverId}:remove`;
      error = null;
      await stopMcpClientServer(serverId);
      runtimeServers = runtimeServers.filter((s) => s.server_id !== serverId);
      runtimeTools = runtimeTools.filter((t) => t.server_id !== serverId);
      if (selectedRuntimeTool.startsWith(`${serverId}.`)) {
        selectedRuntimeTool = '';
      }
      statusMessage = `Removed server "${serverId}" from dashboard.`;
    } catch (err) {
      error = err instanceof Error ? err.message : `Failed to remove ${serverId}`;
    } finally {
      runtimeActionLoading = '';
    }
  }

  function updatePermissionField(
    serverId: string,
    field: 'allowInput' | 'denyInput' | 'confirmInput',
    value: string
  ) {
    const current = permissionDrafts[serverId];
    if (!current) return;
    permissionDrafts = {
      ...permissionDrafts,
      [serverId]: {
        ...current,
        [field]: value,
      },
    };
  }

  function togglePermissionFlag(serverId: string, field: 'enabled' | 'auto_start') {
    const current = permissionDrafts[serverId];
    if (!current) return;
    permissionDrafts = {
      ...permissionDrafts,
      [serverId]: {
        ...current,
        [field]: !current[field],
      },
    };
  }

  function mergeRuleInput(currentValue: string, nextRules: string[]): string {
    return Array.from(new Set([...splitRules(currentValue), ...nextRules])).join(', ');
  }

  function applyBulkPermissionPreset(mode: 'read' | 'write') {
    const nextDrafts = { ...permissionDrafts };
    for (const [serverId, draft] of Object.entries(nextDrafts)) {
      nextDrafts[serverId] = {
        ...draft,
        allowInput:
          mode === 'read'
            ? mergeRuleInput(draft.allowInput, ['get_*', 'list_*', 'read_*', 'search_*', 'status_*', 'view_*'])
            : draft.allowInput,
        confirmInput:
          mode === 'write'
            ? mergeRuleInput(draft.confirmInput, ['create_*', 'delete_*', 'move_*', 'run_*', 'update_*', 'write_*'])
            : draft.confirmInput,
      };
    }
    permissionDrafts = nextDrafts;
    statusMessage = mode === 'read' ? 'Added read-only allow patterns.' : 'Added write-confirm patterns.';
  }

  async function savePermissions() {
    try {
      permissionsSaving = true;
      error = null;
      const servers = Object.fromEntries(
        Object.entries(permissionDrafts).map(([serverId, draft]) => [
          serverId,
          {
            enabled: draft.enabled,
            auto_start: draft.auto_start,
            permissions: {
              allow: splitRules(draft.allowInput),
              deny: splitRules(draft.denyInput),
              confirm: splitRules(draft.confirmInput),
            } satisfies McpPermissionRules,
          },
        ])
      );

      permissionData = await updateMcpClientPermissions({
        client: selectedClient,
        project_root: projectRoot || undefined,
        servers,
      });
      initializePermissionDrafts(permissionData);
      statusMessage = 'Permission settings saved.';
      await refreshStatus();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to save MCP permission settings';
    } finally {
      permissionsSaving = false;
    }
  }

  function formatJson(value: unknown): string {
    return JSON.stringify(value ?? {}, null, 2);
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

  async function resetConfiguredServers() {
    const configuredServerIds = Object.keys(statusData?.configured ?? {});
    const targetServerIds = selectedServerIds.filter((serverId) => configuredServerIds.includes(serverId));
    const serverIds = targetServerIds.length > 0 ? targetServerIds : configuredServerIds;

    if (serverIds.length === 0) {
      statusMessage = 'No applied MCP config to clear yet.';
      return;
    }

    const scopeLabel = targetServerIds.length > 0 ? 'the selected MCP server entries' : 'all configured MCP server entries';
    if (typeof window !== 'undefined' && !window.confirm(`Remove ${scopeLabel} from ${selectedClient}?`)) {
      return;
    }

    try {
      actionLoading = true;
      error = null;
      copyMessage = '';
      preview = null;
      const result = await resetMcpConfig({
        client: selectedClient,
        server_ids: serverIds,
        project_root: projectRoot || undefined,
      });

      selectedServerIds = selectedServerIds.filter((serverId) => !result.removed_server_ids.includes(serverId));
      envValues = {};
      argValues = {};
      statusMessage = result.count > 0
        ? `Removed ${result.removed_server_ids.join(', ')} from ${selectedClient}${result.path ? ` (${result.path})` : ''}.`
        : 'No matching MCP config entries were found.';

      await refreshStatus();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to clear MCP configuration';
    } finally {
      actionLoading = false;
    }
  }

  async function removeSelectedTool() {
    if (!selectedRuntimeToolInfo) return;
    const { server_id, name, namespace } = selectedRuntimeToolInfo;

    if (typeof window !== 'undefined' && !window.confirm(`Remove tool "${namespace}"? Restart the server to restore it.`)) {
      return;
    }

    try {
      actionLoading = true;
      error = null;
      await removeMcpClientTool(server_id, name);
      runtimeTools = runtimeTools.filter((t) => t.namespace !== namespace);
      selectedRuntimeTool = '';
      statusMessage = `Removed tool "${namespace}". Restart server "${server_id}" to restore it.`;
    } catch (err) {
      error = err instanceof Error ? err.message : `Failed to remove tool "${namespace}"`;
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
  $: selectedRuntimeToolInfo = runtimeTools.find((tool) => tool.namespace === selectedRuntimeTool) ?? null;
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
          <Button
            variant="ghost"
            size="sm"
            on:click={resetConfiguredServers}
            disabled={actionLoading || !selectedClientInfo?.supports_apply || Object.keys(statusData?.configured ?? {}).length === 0}
          >
            Reset config
          </Button>
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

    <section class="card runtime-section">
      <div class="section-title">
        <Server size={18} />
        <div>
          <h2>Live MCP Client Dashboard</h2>
          <p class="muted">View and control the external MCP servers currently available to StratifyAI chat.</p>
        </div>
      </div>

      <div class="action-row secondary-actions">
        <Button variant="secondary" size="sm" on:click={refreshRuntimePanels}>
          <RefreshCw size={14} />
          Refresh live data
        </Button>
      </div>

      {#if dashboardLoading}
        <div class="loading-state">
          <LoadingSpinner size="lg" />
          <span>Loading live MCP client engine state...</span>
        </div>
      {:else if runtimeServers.length === 0}
        <p class="muted">No live MCP client servers are available yet. Configure one above and refresh this dashboard.</p>
      {:else}
        <div class="runtime-server-grid">
          {#each runtimeServers as server (server.server_id)}
            <article class="runtime-card">
              <div class="runtime-card__header">
                <div>
                  <h3>{server.server_id}</h3>
                  <p>{server.tool_count} discovered tool{server.tool_count === 1 ? '' : 's'}</p>
                </div>
                <span class={`status-pill ${server.status}`}>{server.status}</span>
              </div>

              <div class="server-meta">
                <span class="chip">{server.enabled ? 'enabled' : 'disabled'}</span>
                <span class="chip">{server.auto_start ? 'auto-start' : 'manual start'}</span>
              </div>

              {#if server.error}
                <p class="error-inline">{server.error}</p>
              {/if}

              <div class="action-row secondary-actions">
                <Button
                  variant="ghost"
                  size="sm"
                  on:click={() => runServerAction(server.server_id, 'start')}
                  disabled={runtimeActionLoading !== '' || !server.enabled || server.status === 'connected'}
                >
                  <Play size={14} />
                  Start
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  on:click={() => runServerAction(server.server_id, 'stop')}
                  disabled={runtimeActionLoading !== '' || server.status !== 'connected'}
                >
                  <Square size={14} />
                  Stop
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  on:click={() => runServerAction(server.server_id, 'restart')}
                  disabled={runtimeActionLoading !== '' || !server.enabled}
                >
                  <Power size={14} />
                  Restart
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  on:click={() => removeServer(server.server_id)}
                  disabled={runtimeActionLoading !== ''}
                >
                  <Trash2 size={14} />
                  Remove
                </Button>
              </div>
            </article>
          {/each}
        </div>
      {/if}
    </section>

    <div class="runtime-grid">
      <section class="card tool-discovery-panel">
        <div class="section-title">
          <Wrench size={18} />
          <div>
            <h2>Tool Discovery</h2>
            <p class="muted">Browse tools by live server, inspect schemas, and see the current permission mode.</p>
          </div>
        </div>

        {#if runtimeTools.length === 0}
          <p class="muted">No external MCP tools have been discovered yet. Start a server from the dashboard above to populate this panel.</p>
        {:else}
          <div class="tool-browser-layout">
            <div class="tool-list">
              {#each runtimeServers as server (server.server_id)}
                {#if runtimeTools.some((tool) => tool.server_id === server.server_id)}
                  <div class="tool-group">
                    <h3>{server.server_id}</h3>
                    {#each runtimeTools.filter((tool) => tool.server_id === server.server_id) as tool (tool.namespace)}
                      <button
                        class:selected={selectedRuntimeTool === tool.namespace}
                        class="tool-link"
                        on:click={() => selectedRuntimeTool = tool.namespace}
                      >
                        <span>{tool.namespace}</span>
                        <span class={`permission-chip ${tool.permission}`}>{tool.permission}</span>
                      </button>
                    {/each}
                  </div>
                {/if}
              {/each}
            </div>

            <div class="tool-detail-panel">
              {#if selectedRuntimeToolInfo}
                <div class="server-meta">
                  <span class="chip">{selectedRuntimeToolInfo.server_id}</span>
                  <span class={`permission-chip ${selectedRuntimeToolInfo.permission}`}>{selectedRuntimeToolInfo.permission}</span>
                </div>
                <div class="tool-header-row">
                  <h3>{selectedRuntimeToolInfo.namespace}</h3>
                  <Button variant="danger" size="sm" on:click={removeSelectedTool} disabled={actionLoading}>
                    Remove
                  </Button>
                </div>
                <p class="muted">{selectedRuntimeToolInfo.description || 'No tool description provided.'}</p>
                <pre class="preview-output compact">{formatJson(selectedRuntimeToolInfo.input_schema)}</pre>
              {:else}
                <p class="muted">Select a tool to inspect its schema and permission mode.</p>
              {/if}
            </div>
          </div>
        {/if}
      </section>

      <section class="card permission-panel">
        <div class="section-title">
          <Shield size={18} />
          <div>
            <h2>Permission Manager</h2>
            <p class="muted">Set enablement, auto-start, and allow/deny/confirm rules for the selected client config.</p>
          </div>
        </div>

        <div class="action-row secondary-actions">
          <Button variant="ghost" size="sm" on:click={() => applyBulkPermissionPreset('read')}>
            Allow all read-only
          </Button>
          <Button variant="ghost" size="sm" on:click={() => applyBulkPermissionPreset('write')}>
            Confirm write tools
          </Button>
          <Button variant="secondary" size="sm" on:click={savePermissions} loading={permissionsSaving}>
            Save permissions
          </Button>
        </div>

        {#if permissionData?.path}
          <p class="path-text">Editing: {permissionData.path}</p>
        {/if}

        {#if Object.keys(permissionDrafts).length === 0}
          <p class="muted">No configurable MCP permission entries found for this client yet.</p>
        {:else}
          <div class="permission-list">
            {#each Object.entries(permissionDrafts) as [serverId, draft]}
              <article class="permission-card">
                <div class="runtime-card__header">
                  <div>
                    <h3>{serverId}</h3>
                    <p>Pattern-based safety rules for this server</p>
                  </div>
                  <span class="chip">{draft.enabled ? 'enabled' : 'disabled'}</span>
                </div>

                <div class="toggle-grid">
                  <label class="inline-toggle">
                    <input type="checkbox" checked={draft.enabled} on:change={() => togglePermissionFlag(serverId, 'enabled')} />
                    <span>Enabled</span>
                  </label>
                  <label class="inline-toggle">
                    <input type="checkbox" checked={draft.auto_start} on:change={() => togglePermissionFlag(serverId, 'auto_start')} />
                    <span>Auto-start</span>
                  </label>
                </div>

                <div class="permission-grid">
                  <label>
                    <span>Allow patterns</span>
                    <input
                      type="text"
                      value={draft.allowInput}
                      placeholder="read_*, list_*"
                      on:input={(event) => updatePermissionField(serverId, 'allowInput', (event.currentTarget as HTMLInputElement).value)}
                    />
                  </label>
                  <label>
                    <span>Deny patterns</span>
                    <input
                      type="text"
                      value={draft.denyInput}
                      placeholder="delete_secret, shutdown_*"
                      on:input={(event) => updatePermissionField(serverId, 'denyInput', (event.currentTarget as HTMLInputElement).value)}
                    />
                  </label>
                  <label>
                    <span>Confirm patterns</span>
                    <input
                      type="text"
                      value={draft.confirmInput}
                      placeholder="delete_*, write_*"
                      on:input={(event) => updatePermissionField(serverId, 'confirmInput', (event.currentTarget as HTMLInputElement).value)}
                    />
                  </label>
                </div>
              </article>
            {/each}
          </div>
        {/if}
      </section>
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

  .runtime-section,
  .tool-discovery-panel,
  .permission-panel {
    display: flex;
    flex-direction: column;
    gap: $space-3;
  }

  .runtime-grid {
    display: grid;
    gap: $space-4;
    grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);

    @media (max-width: 1200px) {
      grid-template-columns: 1fr;
    }
  }

  .runtime-server-grid {
    display: grid;
    gap: $space-3;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  }

  .runtime-card,
  .permission-card {
    display: flex;
    flex-direction: column;
    gap: $space-3;
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-lg;
    padding: $space-3;
    background: var(--bg-base);

    h3 {
      margin: 0;
      color: var(--text-primary);
      font-size: $text-base;
    }

    p {
      margin: $space-1 0 0;
      color: var(--text-secondary);
      font-size: $text-sm;
    }
  }

  .runtime-card__header {
    display: flex;
    justify-content: space-between;
    gap: $space-3;
    align-items: flex-start;
  }

  .status-pill,
  .permission-chip {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: $space-1 $space-2;
    font-size: $text-xs;
    text-transform: capitalize;
    background: var(--bg-elevated);
    color: var(--text-secondary);
  }

  .status-pill.connected,
  .permission-chip.allow {
    color: #10b981;
  }

  .status-pill.starting,
  .status-pill.stopped,
  .permission-chip.confirm {
    color: #f59e0b;
  }

  .status-pill.error,
  .status-pill.disabled,
  .permission-chip.deny {
    color: #ef4444;
  }

  .error-inline {
    margin: 0;
    color: #ef4444;
    font-size: $text-xs;
  }

  .tool-browser-layout {
    display: grid;
    grid-template-columns: minmax(220px, 0.9fr) minmax(0, 1.2fr);
    gap: $space-3;

    @media (max-width: 900px) {
      grid-template-columns: 1fr;
    }
  }

  .tool-list,
  .tool-group,
  .tool-detail-panel,
  .permission-list {
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }

  .tool-group h3 {
    margin: 0 0 $space-1;
    color: var(--text-primary);
    font-size: $text-sm;
  }

  .tool-link {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $space-2;
    padding: $space-2 $space-3;
    border-radius: $radius-lg;
    border: 1px solid var(--bg-elevated);
    background: var(--bg-base);
    color: var(--text-primary);
    font-size: $text-sm;
    cursor: pointer;
    text-align: left;

    &.selected {
      border-color: var(--accent);
      box-shadow: inset 0 0 0 1px rgba(110, 231, 255, 0.25);
    }
  }

  .tool-detail-panel {
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-lg;
    padding: $space-3;
    background: var(--bg-base);
  }

  .tool-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: $space-2;
  }

  .preview-output.compact {
    min-height: 220px;
    flex: initial;
  }

  .toggle-grid {
    display: flex;
    flex-wrap: wrap;
    gap: $space-3;
  }

  .inline-toggle {
    flex-direction: row;
    align-items: center;
    gap: $space-2;

    input {
      width: auto;
    }
  }

  .permission-grid {
    display: grid;
    gap: $space-3;
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
