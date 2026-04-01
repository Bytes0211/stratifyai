<script lang="ts">
  import { configStore, configActions } from '$lib/stores/config';
  import { Lock, Unlock } from 'lucide-svelte';
  
  function handleChange(e: Event) {
    const target = e.target as HTMLInputElement;
    configActions.setTemperature(parseFloat(target.value));
  }
</script>

<div class="temperature-slider">
  <div class="slider-header">
    <label for="temperature">Temperature</label>
    <span class="temperature-value">
      {$configStore.effectiveTemperature.toFixed(1)}
    </span>
  </div>
  
  {#if $configStore.isReasoningModel}
    <div class="locked-notice">
      <Lock size={14} />
      <span>Locked to 1.0 for reasoning models</span>
    </div>
  {:else}
    <div class="slider-wrapper">
      <input
        type="range"
        id="temperature"
        min="0"
        max="2"
        step="0.1"
        value={$configStore.temperature}
        on:input={handleChange}
      />
      <div class="slider-labels">
        <span>Precise</span>
        <span>Creative</span>
      </div>
    </div>
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .temperature-slider {
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }
  
  .slider-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  label {
    font-size: $text-sm;
    font-weight: $font-medium;
    color: var(--text-secondary);
  }
  
  .temperature-value {
    font-size: $text-sm;
    font-weight: $font-semibold;
    color: var(--accent);
    font-family: $font-mono;
  }
  
  .locked-notice {
    display: flex;
    align-items: center;
    gap: $space-2;
    font-size: $text-xs;
    color: var(--text-muted);
    padding: $space-2;
    background: var(--bg-elevated);
    border-radius: $radius-lg;
  }
  
  .slider-wrapper {
    display: flex;
    flex-direction: column;
    gap: $space-1;
  }
  
  input[type="range"] {
    width: 100%;
    height: 6px;
    appearance: none;
    background: var(--bg-elevated);
    border-radius: $radius-full;
    cursor: pointer;
    
    &::-webkit-slider-thumb {
      appearance: none;
      width: 18px;
      height: 18px;
      background: var(--accent);
      border-radius: 50%;
      cursor: grab;
      transition: transform $transition-fast;
      
      &:hover {
        transform: scale(1.1);
      }
      
      &:active {
        cursor: grabbing;
      }
    }
    
    &::-moz-range-thumb {
      width: 18px;
      height: 18px;
      background: var(--accent);
      border: none;
      border-radius: 50%;
      cursor: grab;
    }
    
    &:focus-visible {
      outline: none;
      
      &::-webkit-slider-thumb {
        box-shadow: 0 0 0 3px var(--bg-base), 0 0 0 5px var(--accent);
      }
    }
  }
  
  .slider-labels {
    display: flex;
    justify-content: space-between;
    font-size: $text-xs;
    color: var(--text-muted);
  }
</style>
