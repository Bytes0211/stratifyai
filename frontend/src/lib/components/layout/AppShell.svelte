<script lang="ts">
  import { onMount } from 'svelte';
  import Header from './Header.svelte';
  import Sidebar from './Sidebar.svelte';
  import ChatContainer from '../chat/ChatContainer.svelte';
  import ChatInput from '../chat/ChatInput.svelte';
  import ModelCatalog from '../catalog/ModelCatalog.svelte';
  
  let sidebarCollapsed = false;
  let currentPage: 'chat' | 'models' = 'chat';
  
  function toggleSidebar() {
    sidebarCollapsed = !sidebarCollapsed;
  }
  
  function navigateTo(page: 'chat' | 'models') {
    currentPage = page;
    const path = page === 'chat' ? '/' : '/models';
    window.history.pushState({}, '', path);
  }
  
  onMount(() => {
    function handlePopState() {
      const path = window.location.pathname;
      currentPage = path === '/models' ? 'models' : 'chat';
    }
    
    // Set initial page from URL
    const path = window.location.pathname;
    currentPage = path === '/models' ? 'models' : 'chat';
    
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  });
</script>

<div class="app-shell" class:sidebar-collapsed={sidebarCollapsed}>
  <Header on:toggleSidebar={toggleSidebar} {currentPage} {navigateTo} />
  
  <div class="app-body">
    {#if currentPage === 'chat'}
      <Sidebar collapsed={sidebarCollapsed} />
      
      <main class="main-content">
        <ChatContainer />
        <ChatInput />
      </main>
    {:else}
      <main class="main-content full-width">
        <ModelCatalog on:navigate={(e) => navigateTo(e.detail.page)} />
      </main>
    {/if}
  </div>
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .app-shell {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background: var(--bg-base);
  }
  
  .app-body {
    display: flex;
    flex: 1;
    overflow: hidden;
  }
  
  .main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0; // Prevent flex item from overflowing
    padding: $space-4;
    gap: $space-4;
    overflow-y: auto;
    
    @include lg {
      padding: $space-6;
    }
    
    &.full-width {
      padding: 0;
    }
  }
</style>
