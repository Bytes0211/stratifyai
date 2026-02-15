<script lang="ts">
  import { costStore, costActions } from '$lib/stores/cost';
  import { DollarSign, Zap, MessageSquare, Trash2 } from 'lucide-svelte';
  import Button from '../shared/Button.svelte';
  
  function formatCost(cost: number): string {
    if (cost === 0) return '$0.00';
    if (cost < 0.01) return `$${cost.toFixed(4)}`;
    return `$${cost.toFixed(2)}`;
  }
  
  function formatTokens(tokens: number): string {
    if (tokens >= 1000000) {
      return `${(tokens / 1000000).toFixed(2)}M`;
    }
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}k`;
    }
    return tokens.toString();
  }
</script>

<div class="cost-summary">
  <h3>Session Costs</h3>
  
  <div class="stats-grid">
    <div class="stat-card">
      <div class="stat-icon cost">
        <DollarSign size={16} />
      </div>
      <div class="stat-content">
        <span class="stat-value">{formatCost($costStore.totalCost)}</span>
        <span class="stat-label">Total Cost</span>
      </div>
    </div>
    
    <div class="stat-card">
      <div class="stat-icon tokens">
        <Zap size={16} />
      </div>
      <div class="stat-content">
        <span class="stat-value">{formatTokens($costStore.totalTokens)}</span>
        <span class="stat-label">Tokens Used</span>
      </div>
    </div>
    
    <div class="stat-card">
      <div class="stat-icon calls">
        <MessageSquare size={16} />
      </div>
      <div class="stat-content">
        <span class="stat-value">{$costStore.totalCalls}</span>
        <span class="stat-label">API Calls</span>
      </div>
    </div>
  </div>
  
  {#if Object.keys($costStore.byProvider).length > 0}
    <div class="breakdown">
      <h4>By Provider</h4>
      <div class="breakdown-list">
        {#each Object.entries($costStore.byProvider) as [provider, data]}
          <div class="breakdown-item">
            <span class="breakdown-name">{provider}</span>
            <span class="breakdown-value">{formatCost(data.cost)}</span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
  
  {#if $costStore.totalCalls > 0}
    <Button variant="ghost" size="sm" on:click={() => costActions.clear()}>
      <Trash2 size={14} />
      Clear Session Data
    </Button>
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .cost-summary {
    display: flex;
    flex-direction: column;
    gap: $space-4;
  }
  
  h3 {
    font-size: $text-sm;
    font-weight: $font-semibold;
    color: var(--text-primary);
    margin: 0;
  }
  
  .stats-grid {
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }
  
  .stat-card {
    display: flex;
    align-items: center;
    gap: $space-3;
    padding: $space-3;
    background: var(--bg-elevated);
    border-radius: $radius-lg;
  }
  
  .stat-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: $radius-md;
    
    &.cost {
      background: rgba($success, 0.15);
      color: $success;
    }
    
    &.tokens {
      background: rgba($info, 0.15);
      color: $info;
    }
    
    &.calls {
      background: rgba($accent-primary, 0.15);
      color: $accent-primary;
    }
  }
  
  .stat-content {
    display: flex;
    flex-direction: column;
  }
  
  .stat-value {
    font-size: $text-lg;
    font-weight: $font-bold;
    color: var(--text-primary);
    font-family: $font-mono;
  }
  
  .stat-label {
    font-size: $text-xs;
    color: var(--text-muted);
  }
  
  .breakdown {
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }
  
  h4 {
    font-size: $text-xs;
    font-weight: $font-medium;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0;
  }
  
  .breakdown-list {
    display: flex;
    flex-direction: column;
    gap: $space-1;
  }
  
  .breakdown-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: $space-2;
    background: var(--bg-elevated);
    border-radius: $radius-md;
    font-size: $text-sm;
  }
  
  .breakdown-name {
    color: var(--text-secondary);
    text-transform: capitalize;
  }
  
  .breakdown-value {
    font-weight: $font-medium;
    color: var(--text-primary);
    font-family: $font-mono;
  }
</style>
