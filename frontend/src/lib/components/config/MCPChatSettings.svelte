<script lang="ts">
  import { onMount } from 'svelte';
  import { configStore } from '$lib/stores/config';
  import { mcpRuntimeActions, mcpRuntimeStore } from '$lib/stores/mcp';
  import { Bot, Loader } from 'lucide-svelte';

  onMount(() => {
    void mcpRuntimeActions.ensureLoaded();
  });

  $: availableServers = $mcpRuntimeStore.servers.filter((server) => server.enabled);
  $: activeCount = $configStore.activeMcpServers.length;
  $: activeNames = $configStore.activeMcpServers.slice(0, 3).join(', ');
  $: overflow = $configStore.activeMcpServers.length > 3 ? ` +${$configStore.activeMcpServers.length - 3}` : '';
</script>

<div class="mcp-summary">
  <div class="summary-row">
    <Bot size={14} />
    {#if $mcpRuntimeStore.loading}
      <Loader size={12} class="spin" />
      <span>MCP Tools: loading…</span>
    {:else if availableServers.length === 0}
      <span class="muted">MCP Tools: not configured</span>
    {:else if activeCount > 0}
      <span>MCP Tools: <strong>{activeCount} active</strong></span>
    {:else}
      <span class="muted">MCP Tools: none active</span>
    {/if}
  </div>
  {#if activeCount > 0 && !$mcpRuntimeStore.loading}
    <div class="active-names">{activeNames}{overflow}</div>
  {/if}
  {#if availableServers.length > 0}
    <small class="hint">Manage servers in the panel below the chat</small>
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;

  .mcp-summary {
    display: flex;
    flex-direction: column;
    gap: $space-1;
    padding: $space-2 0;
    border-top: 1px solid var(--bg-elevated);
  }

  .summary-row {
    display: flex;
    align-items: center;
    gap: $space-2;
    font-size: $text-xs;
    color: var(--text-secondary);

    strong {
      color: var(--text-primary);
    }
  }

  .muted {
    color: var(--text-muted);
  }

  .active-names {
    font-size: $text-xs;
    color: var(--text-secondary);
    padding-left: 22px; // align with text after icon
    line-height: 1.3;
  }

  .hint {
    font-size: 10px;
    color: var(--text-muted);
    padding-left: 22px;
  }

  :global(.spin) {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
</style>
