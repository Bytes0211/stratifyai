<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { configStore, configActions } from '$lib/stores/config';
  import { getModels } from '$lib/api/client';
  import { PROVIDERS, type Provider, type ModelInfo } from '$lib/api/types';
  import ProviderBadge from './ProviderBadge.svelte';
  import LoadingSpinner from '../shared/LoadingSpinner.svelte';
  import { ChevronDown, AlertCircle, CheckCircle } from 'lucide-svelte';
  
  let models: ModelInfo[] = [];
  let loading = false;
  let error: string | null = null;
  let validated = false;
  let apiKeySet = false;
  
  // Load models when provider changes
  $: loadModels($configStore.provider);
  
  async function loadModels(provider: Provider) {
    loading = true;
    error = null;
    models = [];
    
    try {
      const response = await getModels(provider);
      models = response.models;
      validated = response.validation.validated;
      apiKeySet = response.validation.api_key_set;
      
      // Check if current model exists in loaded models
      const config = get(configStore);
      const currentModelExists = config.model && models.some(m => m.id === config.model);
      
      // Auto-select first model if none selected OR current model not in list
      if (models.length > 0 && (!config.model || !currentModelExists)) {
        // If model was set but not in list, try to find a match by display name
        if (config.model && !currentModelExists) {
          const matchByName = models.find(m => 
            m.display_name.toLowerCase() === config.modelInfo?.display_name?.toLowerCase()
          );
          if (matchByName) {
            configActions.setModel(matchByName.id, matchByName);
          } else {
            // Fall back to first model
            const firstModel = models[0];
            configActions.setModel(firstModel.id, firstModel);
          }
        } else {
          const firstModel = models[0];
          configActions.setModel(firstModel.id, firstModel);
        }
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load models';
    } finally {
      loading = false;
    }
  }
  
  function handleProviderChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    configActions.setProvider(target.value as Provider);
  }
  
  function handleModelChange(e: Event) {
    const target = e.target as HTMLSelectElement;
    const model = models.find(m => m.id === target.value);
    if (model) {
      configActions.setModel(model.id, model);
    }
  }
  
  // Group models by category
  $: groupedModels = (() => {
    const groups: Record<string, ModelInfo[]> = {};
    for (const model of models) {
      const category = model.category || 'Other';
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(model);
    }
    return groups;
  })();
</script>

<div class="model-selector">
  <div class="form-group">
    <label for="provider-select">Provider</label>
    <div class="select-wrapper">
      <select 
        id="provider-select"
        value={$configStore.provider}
        on:change={handleProviderChange}
      >
        {#each PROVIDERS as provider}
          <option value={provider}>{provider}</option>
        {/each}
      </select>
      <ChevronDown size={16} class="select-icon" />
    </div>
    <div class="provider-info">
      <ProviderBadge provider={$configStore.provider} />
    </div>
  </div>
  
  <div class="form-group">
    <label for="model-select">Model</label>
    {#if loading}
      <div class="loading-state">
        <LoadingSpinner size="sm" />
        <span>Loading models...</span>
      </div>
    {:else if error}
      <div class="error-state">
        <AlertCircle size={14} />
        <span>{error}</span>
      </div>
    {:else}
      <div class="select-wrapper">
        <select 
          id="model-select"
          value={$configStore.model}
          on:change={handleModelChange}
          disabled={models.length === 0}
        >
          {#if models.length === 0}
            <option value="">No models available</option>
          {:else}
            {#each Object.entries(groupedModels) as [category, categoryModels]}
              <optgroup label={category}>
                {#each categoryModels as model}
                  <option value={model.id}>{model.display_name}</option>
                {/each}
              </optgroup>
            {/each}
          {/if}
        </select>
        <ChevronDown size={16} class="select-icon" />
      </div>
      
      <div class="validation-status">
        {#if apiKeySet}
          <span class="status success">
            <CheckCircle size={12} />
            API key configured
          </span>
        {:else}
          <span class="status warning">
            <AlertCircle size={12} />
            API key not set
          </span>
        {/if}
      </div>
    {/if}
  </div>
  
  {#if $configStore.modelInfo}
    <div class="model-info">
      {#if $configStore.isReasoningModel}
        <span class="model-badge reasoning">Reasoning</span>
      {/if}
      {#if $configStore.supportsVision}
        <span class="model-badge vision">Vision</span>
      {/if}
    </div>
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .model-selector {
    display: flex;
    flex-direction: column;
    gap: $space-4;
  }
  
  .form-group {
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }
  
  label {
    font-size: $text-sm;
    font-weight: $font-medium;
    color: var(--text-secondary);
  }
  
  .select-wrapper {
    position: relative;
    
    select {
      width: 100%;
      appearance: none;
      padding: $space-2 $space-8 $space-2 $space-3;
      font-size: $text-sm;
      color: var(--text-primary);
      background: var(--bg-elevated);
      border: 1px solid var(--bg-hover);
      border-radius: $radius-lg;
      cursor: pointer;
      @include focus-visible-ring;
      
      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }
    
    :global(.select-icon) {
      position: absolute;
      right: $space-3;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      pointer-events: none;
    }
  }
  
  .provider-info {
    margin-top: $space-1;
  }
  
  .loading-state,
  .error-state {
    display: flex;
    align-items: center;
    gap: $space-2;
    font-size: $text-sm;
    color: var(--text-secondary);
    padding: $space-2;
  }
  
  .error-state {
    color: $error;
  }
  
  .validation-status {
    margin-top: $space-1;
  }
  
  .status {
    display: inline-flex;
    align-items: center;
    gap: $space-1;
    font-size: $text-xs;
    
    &.success {
      color: $success;
    }
    
    &.warning {
      color: $warning;
    }
  }
  
  .model-info {
    display: flex;
    flex-wrap: wrap;
    gap: $space-2;
  }
  
  .model-badge {
    font-size: $text-xs;
    padding: 2px $space-2;
    border-radius: $radius-full;
    
    &.reasoning {
      background: rgba($info, 0.15);
      color: $info;
    }
    
    &.vision {
      background: rgba($success, 0.15);
      color: $success;
    }
  }
</style>
