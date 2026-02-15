<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { CatalogModel, Provider } from '$lib/api/types';
  import CapabilityBadge from './CapabilityBadge.svelte';
  import ProviderBadge from '../config/ProviderBadge.svelte';
  import { AlertTriangle, ArrowRight } from 'lucide-svelte';
  
  export let model: CatalogModel;
  export let provider: Provider;
  
  const dispatch = createEventDispatcher<{
    select: { provider: Provider; model: CatalogModel };
  }>();
  
  function formatContextWindow(tokens: number): string {
    if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
    if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(0)}k`;
    return tokens.toString();
  }
  
  function handleClick() {
    if (!model.deprecated) {
      dispatch('select', { provider, model });
    }
  }
  
  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }
</script>

<div 
  class="model-card" 
  class:deprecated={model.deprecated}
  class:clickable={!model.deprecated}
  role="button"
  tabindex={model.deprecated ? -1 : 0}
  on:click={handleClick}
  on:keydown={handleKeydown}
>
  <div class="card-header">
    <div class="model-name">
      <span class="name">{model.display_name}</span>
      {#if model.deprecated}
        <span class="deprecated-badge">
          <AlertTriangle size={12} />
          Deprecated
        </span>
      {/if}
    </div>
    <ProviderBadge {provider} size="sm" />
  </div>
  
  <div class="model-id">{model.model_id}</div>
  
  {#if model.description}
    <p class="model-description">{model.description}</p>
  {/if}
  
  <div class="capabilities">
    {#if model.supports_vision}
      <CapabilityBadge type="vision" />
    {/if}
    {#if model.supports_tools}
      <CapabilityBadge type="tools" />
    {/if}
    {#if model.is_reasoning_model}
      <CapabilityBadge type="reasoning" />
    {/if}
  </div>
  
  <div class="model-stats">
    <div class="stat">
      <span class="stat-label">Context</span>
      <span class="stat-value">{formatContextWindow(model.context_window)}</span>
    </div>
    <div class="stat">
      <span class="stat-label">Input</span>
      <span class="stat-value">${model.input_cost_per_1m.toFixed(2)}/1M</span>
    </div>
    <div class="stat">
      <span class="stat-label">Output</span>
      <span class="stat-value">${model.output_cost_per_1m.toFixed(2)}/1M</span>
    </div>
  </div>
  
  {#if model.deprecated && model.replacement_model}
    <div class="replacement-notice">
      Use <code>{model.replacement_model}</code> instead
    </div>
  {/if}
  
  {#if !model.deprecated}
    <div class="select-hint">
      <span>Select model</span>
      <ArrowRight size={14} />
    </div>
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .model-card {
    padding: $space-4;
    background: var(--bg-surface);
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-xl;
    transition: all $transition-fast;
    
    &.clickable {
      cursor: pointer;
      
      &:hover {
        border-color: var(--accent);
        box-shadow: $shadow-md;
        
        .select-hint {
          opacity: 1;
        }
      }
      
      &:focus-visible {
        outline: 2px solid var(--accent);
        outline-offset: 2px;
      }
    }
    
    &:hover:not(.clickable) {
      border-color: var(--bg-hover);
    }
    
    &.deprecated {
      opacity: 0.7;
      border-color: rgba($warning, 0.3);
      cursor: not-allowed;
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: $space-2;
    margin-bottom: $space-2;
  }
  
  .model-name {
    display: flex;
    align-items: center;
    gap: $space-2;
    flex-wrap: wrap;
  }
  
  .name {
    font-size: $text-base;
    font-weight: $font-semibold;
    color: var(--text-primary);
  }
  
  .deprecated-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: $text-xs;
    padding: 2px $space-2;
    background: rgba($warning, 0.15);
    color: $warning;
    border-radius: $radius-full;
  }
  
  .model-id {
    font-size: $text-xs;
    font-family: $font-mono;
    color: var(--text-muted);
    margin-bottom: $space-2;
  }
  
  .model-description {
    font-size: $text-sm;
    color: var(--text-secondary);
    line-height: $leading-relaxed;
    margin-bottom: $space-3;
    @include line-clamp(2);
  }
  
  .capabilities {
    display: flex;
    flex-wrap: wrap;
    gap: $space-2;
    margin-bottom: $space-3;
  }
  
  .model-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: $space-2;
    padding: $space-3;
    background: var(--bg-elevated);
    border-radius: $radius-lg;
  }
  
  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  
  .stat-label {
    font-size: $text-xs;
    color: var(--text-muted);
    margin-bottom: 2px;
  }
  
  .stat-value {
    font-size: $text-sm;
    font-weight: $font-medium;
    color: var(--text-primary);
    font-family: $font-mono;
  }
  
  .replacement-notice {
    margin-top: $space-3;
    padding: $space-2;
    font-size: $text-xs;
    color: var(--text-secondary);
    background: rgba($warning, 0.1);
    border-radius: $radius-md;
    
    code {
      font-family: $font-mono;
      color: var(--accent);
    }
  }
  
  .select-hint {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: $space-1;
    margin-top: $space-3;
    padding-top: $space-3;
    border-top: 1px solid var(--bg-elevated);
    font-size: $text-xs;
    color: var(--accent);
    opacity: 0;
    transition: opacity $transition-fast;
  }
</style>
