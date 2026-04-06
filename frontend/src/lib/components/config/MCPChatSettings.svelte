<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { getMcpClientServers } from '$lib/api/client';
  import type { McpClientServerInfo } from '$lib/api/types';
  import { configActions, configStore } from '$lib/stores/config';
  import Button from '../shared/Button.svelte';
  import LoadingSpinner from '../shared/LoadingSpinner.svelte';
  import { Bot, RefreshCw, ShieldCheck } from 'lucide-svelte';

  let servers: McpClientServerInfo[] = [];
  let loading = false;
  let error: string | null = null;

  onMount(() => {
    void loadServers();
  });

  async function loadServers() {
    try {
      loading = true;
      error = null;
      const response = await getMcpClientServers(true);
      servers = response.servers;

      const availableIds = new Set(
        response.servers
          .filter((server) => server.enabled && server.status !== 'disabled')
          .map((server) => server.server_id)
      );
      const currentSelection = get(configStore).activeMcpServers;
      const filtered = currentSelection.filter((serverId) => availableIds.has(serverId));
      if (filtered.length !== currentSelection.length) {
        configActions.setActiveMcpServers(filtered);
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load MCP chat servers';
      servers = [];
    } finally {
      loading = false;
    }
  }

  function toggleServer(serverId: string) {
    configActions.toggleActiveMcpServer(serverId);
  }

  function canUseInChat(server: McpClientServerInfo): boolean {
    return server.enabled && server.status !== 'disabled' && server.status !== 'error';
  }

  $: availableServers = servers.filter((server) => server.enabled);
</script>

<div class="mcp-chat-settings">
  <div class="section-header">
    <div>
      <h3>MCP Tools in Chat</h3>
      <p>Select which live MCP servers the assistant may use in this conversation.</p>
    </div>
    <Button variant="ghost" size="sm" on:click={loadServers}>
      <RefreshCw size={14} />
      Refresh
    </Button>
  </div>

  {#if loading}
    <div class="loading-state">
      <LoadingSpinner size="sm" />
      <span>Loading MCP servers...</span>
    </div>
  {:else if error}
    <p class="error-text">{error}</p>
  {:else if availableServers.length === 0}
    <div class="empty-state">
      <ShieldCheck size={16} />
      <span>No enabled MCP client servers detected. Configure them from the MCP tab first.</span>
    </div>
  {:else}
    <div class="server-list">
      {#each availableServers as server (server.server_id)}
        <label class="server-option" class:inactive={!canUseInChat(server)}>
          <input
            type="checkbox"
            checked={$configStore.activeMcpServers.includes(server.server_id)}
            disabled={!canUseInChat(server)}
            on:change={() => toggleServer(server.server_id)}
          />
          <div class="server-copy">
            <div class="server-title-row">
              <strong>{server.server_id}</strong>
              <span class={`status-chip ${server.status}`}>{server.status}</span>
            </div>
            <span>{server.tool_count} discovered tool{server.tool_count === 1 ? '' : 's'}</span>
            {#if server.source_client}
              <small>Loaded from {server.source_client}</small>
            {/if}
            {#if server.tools.length > 0}
              <small>{server.tools.slice(0, 2).join(' • ')}{server.tools.length > 2 ? ' …' : ''}</small>
            {/if}
          </div>
        </label>
      {/each}
    </div>

    {#if $configStore.activeMcpServers.length > 0}
      <div class="selection-summary">
        <Bot size={14} />
        <span>Active for chat: {$configStore.activeMcpServers.join(', ')}</span>
      </div>
    {/if}
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;

  .mcp-chat-settings {
    display: flex;
    flex-direction: column;
    gap: $space-3;
    padding-top: $space-2;
    border-top: 1px solid var(--bg-elevated);
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    gap: $space-2;
    align-items: flex-start;

    h3 {
      margin: 0 0 $space-1;
      font-size: $text-sm;
      color: var(--text-primary);
    }

    p {
      margin: 0;
      color: var(--text-secondary);
      font-size: $text-xs;
      line-height: 1.4;
    }
  }

  .loading-state,
  .empty-state,
  .selection-summary {
    display: flex;
    align-items: center;
    gap: $space-2;
    font-size: $text-xs;
    color: var(--text-secondary);
  }

  .empty-state,
  .selection-summary {
    padding: $space-2;
    border-radius: $radius-md;
    background: var(--bg-elevated);
  }

  .server-list {
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }

  .server-option {
    display: flex;
    gap: $space-2;
    align-items: flex-start;
    padding: $space-2;
    border-radius: $radius-lg;
    background: var(--bg-elevated);
    border: 1px solid transparent;
    cursor: pointer;

    &:hover {
      border-color: var(--bg-hover);
    }

    &.inactive {
      opacity: 0.7;
      cursor: not-allowed;
    }

    input {
      margin-top: 2px;
    }
  }

  .server-copy {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;

    strong {
      color: var(--text-primary);
      font-size: $text-sm;
    }

    span,
    small {
      color: var(--text-secondary);
      font-size: $text-xs;
      line-height: 1.4;
    }
  }

  .server-title-row {
    display: flex;
    align-items: center;
    gap: $space-2;
    flex-wrap: wrap;
  }

  .status-chip {
    display: inline-flex;
    align-items: center;
    padding: 1px $space-2;
    border-radius: 999px;
    font-size: 11px;
    text-transform: capitalize;
    background: var(--bg-base);
    color: var(--text-secondary);

    &.connected {
      color: #10b981;
    }

    &.error,
    &.disabled {
      color: #ef4444;
    }

    &.starting,
    &.stopped {
      color: #f59e0b;
    }
  }

  .error-text {
    margin: 0;
    color: #ef4444;
    font-size: $text-xs;
  }
</style>
