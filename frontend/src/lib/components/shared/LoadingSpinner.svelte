<script lang="ts">
  export let size: 'sm' | 'md' | 'lg' = 'md';
</script>

<div class="spinner {size}" aria-label="Loading">
  <div class="spinner-ring"></div>
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  
  .spinner {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    
    &.sm {
      width: 16px;
      height: 16px;
    }
    
    &.md {
      width: 24px;
      height: 24px;
    }
    
    &.lg {
      width: 36px;
      height: 36px;
    }
  }
  
  .spinner-ring {
    width: 100%;
    height: 100%;
    border: 2px solid var(--bg-elevated);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
