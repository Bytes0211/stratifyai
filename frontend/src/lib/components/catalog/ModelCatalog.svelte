<script lang="ts">
  import { onMount } from 'svelte';
  import { createEventDispatcher } from 'svelte';
  import { getCatalog } from '$lib/api/client';
  import type { FullCatalog, CatalogModel, Provider, ModelInfo } from '$lib/api/types';
  import { configActions } from '$lib/stores/config';
  import ModelCard from './ModelCard.svelte';
  import ModelFilters from './ModelFilters.svelte';
  import LoadingSpinner from '../shared/LoadingSpinner.svelte';
  import { AlertCircle, Package } from 'lucide-svelte';
  
  const dispatch = createEventDispatcher();
  
  let catalog: FullCatalog | null = null;
  let loading = true;
  let error: string | null = null;
  
  // Filter state
  let selectedProvider: Provider | 'all' = 'all';
  let searchQuery = '';
  let showVisionOnly = false;
  let showToolsOnly = false;
  let showReasoningOnly = false;
  let showLargeContextOnly = false;
  
  // Reset all filters
  function resetFilters() {
    selectedProvider = 'all';
    searchQuery = '';
    showVisionOnly = false;
    showToolsOnly = false;
    showReasoningOnly = false;
    showLargeContextOnly = false;
  }
  
  // Load catalog on mount
  onMount(() => {
    loadCatalog();
  });
  
  async function loadCatalog() {
    try {
      loading = true;
      error = null;
      catalog = await getCatalog();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load catalog';
    } finally {
      loading = false;
    }
  }
  
  // Helper function to filter models
  function filterModels(
    cat: FullCatalog | null,
    provider: Provider | 'all',
    query: string,
    vision: boolean,
    tools: boolean,
    reasoning: boolean,
    largeContext: boolean
  ): { provider: Provider; model: CatalogModel }[] {
    if (!cat) return [];
    
    const results: { provider: Provider; model: CatalogModel }[] = [];
    
    for (const [prov, models] of Object.entries(cat)) {
      // Filter by provider
      if (provider !== 'all' && prov !== provider) continue;
      
      for (const [, model] of Object.entries(models)) {
        // Search filter
        if (query) {
          const q = query.toLowerCase();
          const matchesSearch = 
            model.display_name.toLowerCase().includes(q) ||
            model.model_id.toLowerCase().includes(q) ||
            (model.description?.toLowerCase().includes(q) ?? false);
          if (!matchesSearch) continue;
        }
        
        // Capability filters - only include models that HAVE the capability
        if (vision && model.supports_vision !== true) continue;
        if (tools && model.supports_tools !== true) continue;
        if (reasoning && model.is_reasoning_model !== true) continue;
        if (largeContext && model.context_window < 1_000_000) continue;
        
        results.push({ provider: prov as Provider, model });
      }
    }
    
    // Sort: non-deprecated first, then by provider, then by name
    return results.sort((a, b) => {
      if (a.model.deprecated !== b.model.deprecated) {
        return a.model.deprecated ? 1 : -1;
      }
      if (a.provider !== b.provider) {
        return a.provider.localeCompare(b.provider);
      }
      return a.model.display_name.localeCompare(b.model.display_name);
    });
  }
  
  // Reactive filtered models - explicitly pass all filter dependencies
  $: filteredModels = filterModels(
    catalog,
    selectedProvider,
    searchQuery,
    showVisionOnly,
    showToolsOnly,
    showReasoningOnly,
    showLargeContextOnly
  );
  
  // Stats
  $: totalModels = catalog 
    ? Object.values(catalog).reduce((sum, models) => sum + Object.keys(models).length, 0)
    : 0;
  
  // Handle model selection
  function handleModelSelect(event: CustomEvent<{ provider: Provider; model: CatalogModel }>) {
    const { provider, model } = event.detail;
    
    // Convert CatalogModel to ModelInfo format for the config store
    const modelInfo: ModelInfo = {
      id: model.model_id,
      display_name: model.display_name,
      description: model.description,
      category: model.category,
      reasoning_model: model.is_reasoning_model,
      supports_vision: model.supports_vision,
    };
    
    // Set provider first (this clears the model)
    configActions.setProvider(provider);
    // Then set the model
    configActions.setModel(model.model_id, modelInfo);
    
    // Dispatch navigation event
    dispatch('navigate', { page: 'chat' });
  }
</script>

<div class="model-catalog">
  <div class="catalog-header">
    <h1>Model Catalog</h1>
    <p>Browse and compare models across all providers</p>
  </div>
  
  <ModelFilters
    {selectedProvider}
    {searchQuery}
    {showVisionOnly}
    {showToolsOnly}
    {showReasoningOnly}
    {showLargeContextOnly}
    on:providerChange={(e) => selectedProvider = e.detail}
    on:searchChange={(e) => searchQuery = e.detail}
    on:visionToggle={() => showVisionOnly = !showVisionOnly}
    on:toolsToggle={() => showToolsOnly = !showToolsOnly}
    on:reasoningToggle={() => showReasoningOnly = !showReasoningOnly}
    on:largeContextToggle={() => showLargeContextOnly = !showLargeContextOnly}
    on:reset={resetFilters}
  />
  
  {#if loading}
    <div class="loading-state">
      <LoadingSpinner size="lg" />
      <span>Loading model catalog...</span>
    </div>
  {:else if error}
    <div class="error-state">
      <AlertCircle size={24} />
      <span>{error}</span>
      <button on:click={loadCatalog}>Try again</button>
    </div>
  {:else if filteredModels.length === 0}
    <div class="empty-state">
      <Package size={32} />
      <span>No models found</span>
      <p>Try adjusting your filters or search query</p>
    </div>
  {:else}
    <div class="results-info">
      Showing {filteredModels.length} of {totalModels} models
    </div>
    
    <div class="model-grid">
      {#each filteredModels as { provider, model } (model.model_id)}
        <ModelCard {model} {provider} on:select={handleModelSelect} />
      {/each}
    </div>
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .model-catalog {
    display: flex;
    flex-direction: column;
    gap: $space-4;
    max-width: 1400px;
    margin: 0 auto;
    padding: $space-4;
    
    @include lg {
      padding: $space-6;
    }
  }
  
  .catalog-header {
    h1 {
      font-size: $text-2xl;
      font-weight: $font-bold;
      color: var(--text-primary);
      margin-bottom: $space-1;
    }
    
    p {
      font-size: $text-sm;
      color: var(--text-secondary);
    }
  }
  
  .loading-state,
  .error-state,
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: $space-3;
    padding: $space-12;
    text-align: center;
    color: var(--text-secondary);
  }
  
  .error-state {
    color: $error;
    
    button {
      margin-top: $space-2;
      padding: $space-2 $space-4;
      font-size: $text-sm;
      color: var(--text-primary);
      background: var(--bg-elevated);
      border: 1px solid var(--bg-hover);
      border-radius: $radius-lg;
      cursor: pointer;
      
      &:hover {
        background: var(--bg-hover);
      }
    }
  }
  
  .empty-state {
    p {
      font-size: $text-sm;
      color: var(--text-muted);
    }
  }
  
  .results-info {
    font-size: $text-sm;
    color: var(--text-muted);
  }
  
  .model-grid {
    display: grid;
    gap: $space-4;
    grid-template-columns: 1fr;
    
    @include md {
      grid-template-columns: repeat(2, 1fr);
    }
    
    @include xl {
      grid-template-columns: repeat(3, 1fr);
    }
  }
</style>
