<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'ghost' | 'danger' = 'primary';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let disabled = false;
  export let loading = false;
  export let type: 'button' | 'submit' | 'reset' = 'button';
</script>

<button 
  class="button {variant} {size}"
  {type}
  disabled={disabled || loading}
  on:click
>
  {#if loading}
    <span class="spinner"></span>
  {/if}
  <slot />
</button>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: $space-2;
    font-family: $font-sans;
    font-weight: $font-medium;
    border-radius: $radius-lg;
    border: none;
    cursor: pointer;
    transition: all $transition-fast;
    @include focus-visible-ring;
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }
    
    // Sizes
    &.sm {
      font-size: $text-xs;
      padding: $space-1 $space-2;
    }
    
    &.md {
      font-size: $text-sm;
      padding: $space-2 $space-4;
    }
    
    &.lg {
      font-size: $text-base;
      padding: $space-3 $space-6;
    }
    
    // Variants
    &.primary {
      background: var(--accent);
      color: #0f172a;
      
      &:hover:not(:disabled) {
        background: var(--accent-hover);
      }
    }
    
    &.secondary {
      background: var(--bg-elevated);
      color: var(--text-primary);
      border: 1px solid var(--bg-hover);
      
      &:hover:not(:disabled) {
        background: var(--bg-hover);
      }
    }
    
    &.ghost {
      background: transparent;
      color: var(--text-secondary);
      
      &:hover:not(:disabled) {
        background: var(--bg-elevated);
        color: var(--text-primary);
      }
    }
    
    &.danger {
      background: var(--error);
      color: white;
      
      &:hover:not(:disabled) {
        opacity: 0.9;
      }
    }
  }
  
  .spinner {
    width: 14px;
    height: 14px;
    border: 2px solid currentColor;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }
  
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
