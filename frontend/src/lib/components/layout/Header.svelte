<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Menu } from 'lucide-svelte';
  import appMeta from '../../../../package.json';
  import ThemeToggle from '../shared/ThemeToggle.svelte';
  
  export let currentPage: 'chat' | 'models' | 'mcp' = 'chat';
  export let navigateTo: (page: 'chat' | 'models' | 'mcp') => void;
  
  const dispatch = createEventDispatcher();
  const versionLabel = `v${appMeta.version}`;
  
  function handleNavClick(e: MouseEvent, page: 'chat' | 'models' | 'mcp') {
    e.preventDefault();
    navigateTo(page);
  }
</script>

<header class="header">
  <div class="header-left">
    <button 
      class="menu-button" 
      on:click={() => dispatch('toggleSidebar')}
      aria-label="Toggle sidebar"
    >
      <Menu size={20} />
    </button>
    
    <a href="/" class="logo" on:click={(e) => handleNavClick(e, 'chat')}>
      <img src="/static/stratifyai_trans_logo.png" alt="" class="logo-icon" />
      <span class="logo-text">StratifyAI</span>
      <span class="logo-version" aria-label={`Application version ${versionLabel}`}>{versionLabel}</span>
    </a>
  </div>
  
  <nav class="header-nav">
    <a 
      href="/" 
      class="nav-link" 
      class:active={currentPage === 'chat'}
      on:click={(e) => handleNavClick(e, 'chat')}
    >Chat</a>
    <a 
      href="/models" 
      class="nav-link" 
      class:active={currentPage === 'models'}
      on:click={(e) => handleNavClick(e, 'models')}
    >Models</a>
    <a 
      href="/mcp" 
      class="nav-link" 
      class:active={currentPage === 'mcp'}
      on:click={(e) => handleNavClick(e, 'mcp')}
    >MCP</a>
  </nav>
  
  <div class="header-right">
    <ThemeToggle />
  </div>
</header>

<style lang="scss">
  @use '../../../styles/tokens' as *;
  @use '../../../styles/mixins' as *;
  
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: $space-3 $space-4;
    background: var(--bg-surface);
    border-bottom: 1px solid var(--bg-elevated);
    position: sticky;
    top: 0;
    z-index: $z-sticky;
    
    @include lg {
      padding: $space-3 $space-6;
    }
  }
  
  .header-left {
    display: flex;
    align-items: center;
    gap: $space-3;
  }
  
  .menu-button {
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
    
    @include lg {
      display: none;
    }
  }
  
  .logo {
    display: flex;
    align-items: flex-end;
    gap: $space-2;
    text-decoration: none;
    
    &:hover {
      opacity: 0.9;
    }
  }
  
  .logo-icon {
    width: 32px;
    height: 32px;
    object-fit: contain;
    align-self: center;
  }
  
  .logo-text {
    font-size: $text-lg;
    font-weight: $font-bold;
    color: var(--accent);
    
    @media (max-width: 480px) {
      display: none;
    }
  }

  .logo-version {
    display: inline-flex;
    align-items: center;
    padding: 1px 6px;
    border: 1px solid rgba(59, 130, 246, 0.24);
    border-radius: $radius-full;
    font-size: 0.45rem;
    font-weight: $font-semibold;
    color: var(--text-primary);
    background: var(--bg-elevated);
    line-height: 1.1;
    letter-spacing: 0.02em;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
    margin-bottom: 1px;

    @media (max-width: 480px) {
      padding: 1px 4px;
      font-size: 0.4rem;
    }
  }
  
  .header-nav {
    display: none;
    align-items: center;
    gap: $space-1;
    
    @include md {
      display: flex;
    }
  }
  
  .nav-link {
    padding: $space-2 $space-3;
    font-size: $text-sm;
    font-weight: $font-medium;
    color: var(--text-secondary);
    border-radius: $radius-lg;
    transition: all $transition-fast;
    @include focus-visible-ring;
    
    &:hover {
      background: var(--bg-elevated);
      color: var(--text-primary);
    }
    
    &.active {
      background: var(--bg-elevated);
      color: var(--accent);
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: $space-2;
  }
</style>
