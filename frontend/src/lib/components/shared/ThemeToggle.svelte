<script lang="ts">
  import { Sun, Moon } from 'lucide-svelte';
  import { themeStore, themeActions } from '$lib/stores/theme';
</script>

<button 
  class="theme-toggle"
  on:click={() => themeActions.toggle()}
  aria-label={$themeStore.isDark ? 'Switch to light mode' : 'Switch to dark mode'}
>
  {#if $themeStore.isDark}
    <Sun size={18} />
  {:else}
    <Moon size={18} />
  {/if}
</button>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .theme-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    border-radius: $radius-lg;
    color: var(--text-secondary);
    transition: all $transition-fast;
    @include focus-visible-ring;
    
    &:hover {
      background: var(--bg-elevated);
      color: var(--text-primary);
    }
  }
</style>
