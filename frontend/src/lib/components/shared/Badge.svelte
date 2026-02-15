<script lang="ts">
  export let variant: 'default' | 'success' | 'warning' | 'error' | 'info' | 'provider' = 'default';
  export let providerColor: string | undefined = undefined;
  export let size: 'sm' | 'md' = 'md';
</script>

<span 
  class="badge {variant} {size}"
  style={providerColor ? `--provider-color: ${providerColor}` : ''}
>
  <slot />
</span>

<style lang="scss">
  @use '../../styles/tokens' as *;
  
  .badge {
    display: inline-flex;
    align-items: center;
    gap: $space-1;
    font-family: $font-sans;
    font-weight: $font-medium;
    border-radius: $radius-full;
    white-space: nowrap;
    
    // Sizes
    &.sm {
      font-size: $text-xs;
      padding: 2px $space-2;
    }
    
    &.md {
      font-size: $text-xs;
      padding: $space-1 $space-2;
    }
    
    // Variants
    &.default {
      background: var(--bg-elevated);
      color: var(--text-secondary);
    }
    
    &.success {
      background: rgba($success, 0.15);
      color: $success;
    }
    
    &.warning {
      background: rgba($warning, 0.15);
      color: $warning;
    }
    
    &.error {
      background: rgba($error, 0.15);
      color: $error;
    }
    
    &.info {
      background: rgba($info, 0.15);
      color: $info;
    }
    
    &.provider {
      background: rgba(var(--provider-color), 0.15);
      color: var(--provider-color);
      border: 1px solid currentColor;
    }
  }
</style>
