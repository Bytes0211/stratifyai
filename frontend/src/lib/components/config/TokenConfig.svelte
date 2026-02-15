<script lang="ts">
  import { get } from 'svelte/store';
  import { configStore, configActions } from '$lib/stores/config';
  import { Zap } from 'lucide-svelte';
  
  function handleMaxTokensChange(e: Event) {
    const target = e.target as HTMLInputElement;
    const value = target.value ? parseInt(target.value, 10) : null;
    configActions.setMaxTokens(value);
  }
  
  function handleChunkSizeChange(e: Event) {
    const target = e.target as HTMLInputElement;
    configActions.setChunkSize(parseInt(target.value, 10));
  }
  
  function toggleStream() {
    const config = get(configStore);
    configActions.setStream(!config.stream);
  }
  
  function toggleChunked() {
    const config = get(configStore);
    configActions.setChunked(!config.chunked);
  }
</script>

<div class="token-config">
  <div class="form-group">
    <label for="max-tokens">Max Tokens (optional)</label>
    <input
      type="number"
      id="max-tokens"
      placeholder="Auto"
      min="1"
      max="128000"
      value={$configStore.maxTokens ?? ''}
      on:input={handleMaxTokensChange}
    />
  </div>
  
  <div class="toggle-group">
    <button 
      class="toggle-btn" 
      class:active={$configStore.stream}
      on:click={toggleStream}
      aria-pressed={$configStore.stream}
    >
      <Zap size={14} />
      <span>Stream Response</span>
    </button>
  </div>
  
  <div class="toggle-group">
    <button 
      class="toggle-btn" 
      class:active={$configStore.chunked}
      on:click={toggleChunked}
      aria-pressed={$configStore.chunked}
    >
      <span>Smart Chunking</span>
    </button>
    
    {#if $configStore.chunked}
      <div class="chunk-size">
        <label for="chunk-size">Chunk Size</label>
        <input
          type="range"
          id="chunk-size"
          min="10000"
          max="100000"
          step="5000"
          value={$configStore.chunkSize}
          on:input={handleChunkSizeChange}
        />
        <span class="chunk-value">{($configStore.chunkSize / 1000).toFixed(0)}k chars</span>
      </div>
    {/if}
  </div>
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .token-config {
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
  
  input[type="number"] {
    width: 100%;
    padding: $space-2 $space-3;
    font-size: $text-sm;
    color: var(--text-primary);
    background: var(--bg-elevated);
    border: 1px solid var(--bg-hover);
    border-radius: $radius-lg;
    @include focus-visible-ring;
    
    &::placeholder {
      color: var(--text-muted);
    }
    
    // Hide spin buttons
    &::-webkit-outer-spin-button,
    &::-webkit-inner-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }
    -moz-appearance: textfield;
  }
  
  .toggle-group {
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }
  
  .toggle-btn {
    display: flex;
    align-items: center;
    gap: $space-2;
    width: 100%;
    padding: $space-2 $space-3;
    font-size: $text-sm;
    color: var(--text-secondary);
    background: var(--bg-elevated);
    border: 1px solid var(--bg-hover);
    border-radius: $radius-lg;
    cursor: pointer;
    transition: all $transition-fast;
    @include focus-visible-ring;
    
    &:hover {
      background: var(--bg-hover);
    }
    
    &.active {
      color: var(--accent);
      border-color: var(--accent);
      background: rgba($accent-primary, 0.1);
    }
  }
  
  .chunk-size {
    display: flex;
    flex-direction: column;
    gap: $space-1;
    padding: $space-2;
    background: var(--bg-elevated);
    border-radius: $radius-lg;
    
    label {
      font-size: $text-xs;
    }
    
    input[type="range"] {
      width: 100%;
      height: 4px;
      appearance: none;
      background: var(--bg-hover);
      border-radius: $radius-full;
      cursor: pointer;
      
      &::-webkit-slider-thumb {
        appearance: none;
        width: 14px;
        height: 14px;
        background: var(--accent);
        border-radius: 50%;
        cursor: grab;
      }
    }
    
    .chunk-value {
      font-size: $text-xs;
      color: var(--text-muted);
      font-family: $font-mono;
      text-align: right;
    }
  }
</style>
