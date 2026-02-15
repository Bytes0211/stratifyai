<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { PROVIDERS, type Provider } from '$lib/api/types';
  import { Search, X, RotateCcw } from 'lucide-svelte';
  
  export let selectedProvider: Provider | 'all' = 'all';
  export let searchQuery = '';
  export let showVisionOnly = false;
  export let showToolsOnly = false;
  export let showReasoningOnly = false;
  export let showLargeContextOnly = false;
  
  const dispatch = createEventDispatcher<{
    providerChange: Provider | 'all';
    searchChange: string;
    visionToggle: void;
    toolsToggle: void;
    reasoningToggle: void;
    largeContextToggle: void;
    reset: void;
  }>();
  
  // Check if any filters are active
  $: hasActiveFilters = selectedProvider !== 'all' || 
    searchQuery !== '' || 
    showVisionOnly || 
    showToolsOnly || 
    showReasoningOnly ||
    showLargeContextOnly;
  
  function handleProviderChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    dispatch('providerChange', target.value as Provider | 'all');
  }
  
  function handleSearchInput(e: Event) {
    const target = e.target as HTMLInputElement;
    dispatch('searchChange', target.value);
  }
  
  function clearSearch() {
    dispatch('searchChange', '');
  }
</script>

<div class="model-filters">
  <div class="search-wrapper">
    <Search size={16} class="search-icon" />
    <input
      type="text"
      placeholder="Search models..."
      value={searchQuery}
      on:input={handleSearchInput}
    />
    {#if searchQuery}
      <button class="clear-btn" on:click={clearSearch} aria-label="Clear search">
        <X size={14} />
      </button>
    {/if}
  </div>
  
  <div class="filter-row">
    <select value={selectedProvider} on:change={handleProviderChange}>
      <option value="all">All Providers</option>
      {#each PROVIDERS as provider}
        <option value={provider}>{provider}</option>
      {/each}
    </select>
    
    <div class="capability-filters">
      <button 
        class="filter-btn" 
        class:active={showVisionOnly}
        on:click={() => dispatch('visionToggle')}
      >
        Vision
      </button>
      <button 
        class="filter-btn" 
        class:active={showToolsOnly}
        on:click={() => dispatch('toolsToggle')}
      >
        Tools
      </button>
      <button 
        class="filter-btn" 
        class:active={showReasoningOnly}
        on:click={() => dispatch('reasoningToggle')}
      >
        Reasoning
      </button>
      <button 
        class="filter-btn" 
        class:active={showLargeContextOnly}
        on:click={() => dispatch('largeContextToggle')}
      >
        1M+ Context
      </button>
    </div>
    
    {#if hasActiveFilters}
      <button 
        class="reset-btn"
        on:click={() => dispatch('reset')}
        aria-label="Reset filters"
      >
        <RotateCcw size={14} />
        Reset
      </button>
    {/if}
  </div>
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .model-filters {
    display: flex;
    flex-direction: column;
    gap: $space-3;
    padding: $space-4;
    background: var(--bg-surface);
    border-radius: $radius-xl;
    border: 1px solid var(--bg-elevated);
  }
  
  .search-wrapper {
    position: relative;
    
    :global(.search-icon) {
      position: absolute;
      left: $space-3;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
    }
    
    input {
      width: 100%;
      padding: $space-2 $space-10 $space-2 $space-10;
      font-size: $text-sm;
      color: var(--text-primary);
      background: var(--bg-elevated);
      border: 1px solid var(--bg-hover);
      border-radius: $radius-lg;
      @include focus-visible-ring;
      
      &::placeholder {
        color: var(--text-muted);
      }
    }
    
    .clear-btn {
      position: absolute;
      right: $space-2;
      top: 50%;
      transform: translateY(-50%);
      display: flex;
      align-items: center;
      justify-content: center;
      width: 24px;
      height: 24px;
      border-radius: $radius-md;
      color: var(--text-muted);
      
      &:hover {
        background: var(--bg-hover);
        color: var(--text-primary);
      }
    }
  }
  
  .filter-row {
    display: flex;
    flex-wrap: wrap;
    gap: $space-3;
    align-items: center;
  }
  
  select {
    padding: $space-2 $space-3;
    font-size: $text-sm;
    color: var(--text-primary);
    background: var(--bg-elevated);
    border: 1px solid var(--bg-hover);
    border-radius: $radius-lg;
    cursor: pointer;
    @include focus-visible-ring;
  }
  
  .capability-filters {
    display: flex;
    gap: $space-2;
    flex-wrap: wrap;
  }
  
  .filter-btn {
    padding: $space-1 $space-3;
    font-size: $text-xs;
    font-weight: $font-medium;
    color: var(--text-secondary);
    background: var(--bg-elevated);
    border: 1px solid var(--bg-hover);
    border-radius: $radius-full;
    cursor: pointer;
    transition: all $transition-fast;
    @include focus-visible-ring;
    
    &:hover {
      background: var(--bg-hover);
    }
    
    &.active {
      background: rgba($accent-primary, 0.15);
      border-color: var(--accent);
      color: var(--accent);
    }
  }
  
  .reset-btn {
    display: flex;
    align-items: center;
    gap: $space-1;
    padding: $space-1 $space-3;
    font-size: $text-xs;
    font-weight: $font-medium;
    color: var(--text-muted);
    background: transparent;
    border: 1px solid var(--bg-hover);
    border-radius: $radius-full;
    cursor: pointer;
    transition: all $transition-fast;
    @include focus-visible-ring;
    
    &:hover {
      background: var(--bg-elevated);
      color: var(--text-primary);
      border-color: var(--text-muted);
    }
  }
</style>
