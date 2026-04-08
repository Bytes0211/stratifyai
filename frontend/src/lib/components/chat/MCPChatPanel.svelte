<script lang="ts">
  import { onMount } from 'svelte';
  import type { McpClientServerInfo } from '$lib/api/types';
  import { configActions, configStore } from '$lib/stores/config';
  import { mcpRuntimeActions, mcpRuntimeStore } from '$lib/stores/mcp';
  import Button from '../shared/Button.svelte';
  import LoadingSpinner from '../shared/LoadingSpinner.svelte';
  import { Bot, ChevronDown, ChevronUp, RefreshCw, ShieldCheck, Trash2 } from 'lucide-svelte';

  let expanded = false;

  onMount(() => {
    void mcpRuntimeActions.ensureLoaded();
  });

  function toggleServer(serverId: string) {
    configActions.toggleActiveMcpServer(serverId);
  }

  function canUseInChat(server: McpClientServerInfo): boolean {
    return server.enabled && server.status !== 'disabled' && server.status !== 'error';
  }

  async function removeServer(serverId: string) {
    const server = availableServers.find((item) => item.server_id === serverId);
    const source = server?.source_client ? ` from ${server.source_client}` : '';
    if (typeof window !== 'undefined' && !window.confirm(`Permanently remove "${serverId}"${source}? Use Apply config to add it back.`)) {
      return;
    }
    try {
      await mcpRuntimeActions.removeServer(serverId);
    } catch {
      // Shared store already surfaces the error state.
    }
  }

  $: availableServers = $mcpRuntimeStore.servers.filter((server) => server.enabled);
  $: activeCount = $configStore.activeMcpServers.length;
  $: hasServers = availableServers.length > 0;
</script>

{#if hasServers || $mcpRuntimeStore.loading}
  <div class="mcp-chat-panel">
    <button class="panel-toggle" on:click={() => (expanded = !expanded)} aria-expanded={expanded}>
      <div class="toggle-left">
        <Bot size={14} />
        {#if $mcpRuntimeStore.loading}
          <span>MCP Tools: loading…</span>
        {:else if activeCount > 0}
          <span>MCP Tools: {activeCount} active</span>
        {:else}
          <span>MCP Tools: none active</span>
        {/if}
      </div>
      <div class="toggle-right">
        <Button variant="ghost" size="sm" on:click={(e) => { e.stopPropagation(); mcpRuntimeActions.refresh(true); }}>
          <RefreshCw size={12} />
        </Button>
        {#if expanded}
          <ChevronUp size={14} />
        {:else}
          <ChevronDown size={14} />
        {/if}
      </div>
    </button>

    {#if expanded}
      <div class="panel-body">
        {#if $mcpRuntimeStore.loading}
          <div class="loading-state">
            <LoadingSpinner size="sm" />
            <span>Loading MCP servers…</span>
          </div>
        {:else if $mcpRuntimeStore.error}
          <p class="error-text">{$mcpRuntimeStore.error}</p>
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
                    <button class="remove-btn" title="Permanently remove from MCP config" on:click|preventDefault|stopPropagation={() => removeServer(server.server_id)}>
                      <Trash2 size={12} />
                    </button>
                  </div>
                  <span>{server.tool_count} tool{server.tool_count === 1 ? '' : 's'}</span>
                  {#if server.tools.length > 0}
                    <small>{server.tools.slice(0, 3).join(' • ')}{server.tools.length > 3 ? ' …' : ''}</small>
                  {/if}
                </div>
              </label>
            {/each}
          </div>

          {#if activeCount > 0}
            <div class="selection-summary">
              <ShieldCheck size={12} />
              <span>Active: {$configStore.activeMcpServers.join(', ')}</span>
            </div>
          {/if}
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;

  .mcp-chat-panel {
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-lg;
    background: var(--bg-surface);
    overflow: hidden;
  }

  .panel-toggle {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: $space-2 $space-3;
    background: transparent;
    border: none;
    color: var(--text-secondary);
    font-size: $text-xs;
    cursor: pointer;
    transition: background $transition-fast;

    &:hover {
      background: var(--bg-elevated);
    }
  }

  .toggle-left {
    display: flex;
    align-items: center;
    gap: $space-2;
  }

  .toggle-right {
    display: flex;
    align-items: center;
    gap: $space-1;
  }

  .panel-body {
    max-height: 200px;
    overflow-y: auto;
    padding: $space-2 $space-3 $space-3;
    border-top: 1px solid var(--bg-elevated);
    display: flex;
    flex-direction: column;
    gap: $space-2;
    @include custom-scrollbar;
  }

  .loading-state {
    display: flex;
    align-items: center;
    gap: $space-2;
    font-size: $text-xs;
    color: var(--text-secondary);
  }

  .error-text {
    font-size: $text-xs;
    color: $error;
    margin: 0;
  }

  .selection-summary {
    display: flex;
    align-items: center;
    gap: $space-2;
    font-size: $text-xs;
    color: var(--text-secondary);
    padding: $space-1 $space-2;
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
    border-radius: $radius-md;
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
      font-size: $text-xs;
    }

    span,
    small {
      color: var(--text-secondary);
      font-size: $text-xs;
      line-height: 1.3;
    }
  }

  .server-title-row {
    display: flex;
    align-items: center;
    gap: $space-2;
    flex-wrap: wrap;
  }

  .remove-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-left: auto;
    padding: 2px 4px;
    border: none;
    border-radius: $radius-sm;
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    opacity: 0.6;

    &:hover {
      opacity: 1;
      color: #ef4444;
      background: rgba(239, 68, 68, 0.1);
    }
  }

  .status-chip {
    display: inline-flex;
    align-items: center;
    padding: 1px $space-2;
    border-radius: 999px;
    font-size: 10px;
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
</style>
