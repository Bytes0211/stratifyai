<script lang="ts">
  import ModelSelector from '../config/ModelSelector.svelte';
  import TemperatureSlider from '../config/TemperatureSlider.svelte';
  import TokenConfig from '../config/TokenConfig.svelte';
  import FileUpload from '../config/FileUpload.svelte';
  import CostSummary from '../dashboard/CostSummary.svelte';
  import ChatHistory from '../chat/ChatHistory.svelte';
import { Settings, DollarSign, FileText, History } from 'lucide-svelte';
  
  export let collapsed = false;
  
  let activeTab: 'config' | 'files' | 'history' | 'costs' = 'config';
</script>

<aside class="sidebar" class:collapsed>
  <div class="sidebar-tabs">
    <button 
      class="tab" 
      class:active={activeTab === 'config'}
      on:click={() => activeTab = 'config'}
      aria-label="Configuration"
    >
      <Settings size={18} />
      <span class="tab-label">Config</span>
    </button>
    <button 
      class="tab" 
      class:active={activeTab === 'files'}
      on:click={() => activeTab = 'files'}
      aria-label="File Upload"
    >
      <FileText size={18} />
      <span class="tab-label">Files</span>
    </button>
    <button 
      class="tab" 
      class:active={activeTab === 'history'}
      on:click={() => activeTab = 'history'}
      aria-label="Chat History"
    >
      <History size={18} />
      <span class="tab-label">History</span>
    </button>
    <button 
      class="tab" 
      class:active={activeTab === 'costs'}
      on:click={() => activeTab = 'costs'}
      aria-label="Cost Tracking"
    >
      <DollarSign size={18} />
      <span class="tab-label">Costs</span>
    </button>
  </div>
  
  <div class="sidebar-content">
    {#if activeTab === 'config'}
      <div class="config-section">
        <ModelSelector />
        <TemperatureSlider />
        <TokenConfig />
      </div>
    {:else if activeTab === 'files'}
      <FileUpload />
    {:else if activeTab === 'history'}
      <ChatHistory />
    {:else if activeTab === 'costs'}
      <CostSummary />
    {/if}
  </div>
</aside>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .sidebar {
    width: 320px;
    background: var(--bg-surface);
    border-right: 1px solid var(--bg-elevated);
    display: flex;
    flex-direction: column;
    transition: transform $transition-normal, width $transition-normal;
    
    @media (max-width: 1023px) {
      position: fixed;
      left: 0;
      top: 57px; // Header height
      bottom: 0;
      z-index: $z-dropdown;
      transform: translateX(0);
      
      &.collapsed {
        transform: translateX(-100%);
      }
    }
    
    @include lg {
      position: relative;
      transform: none;
      
      &.collapsed {
        width: 0;
        border: none;
        overflow: hidden;
      }
    }
  }
  
  .sidebar-tabs {
    display: flex;
    border-bottom: 1px solid var(--bg-elevated);
  }
  
  .tab {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $space-2;
    padding: $space-3;
    color: var(--text-secondary);
    transition: all $transition-fast;
    @include focus-visible-ring;
    
    &:hover {
      background: var(--bg-elevated);
      color: var(--text-primary);
    }
    
    &.active {
      color: var(--accent);
      border-bottom: 2px solid var(--accent);
      margin-bottom: -1px;
    }
  }
  
  .tab-label {
    font-size: $text-sm;
    font-weight: $font-medium;
    
    @media (max-width: 380px) {
      display: none;
    }
  }
  
  .sidebar-content {
    flex: 1;
    overflow-y: auto;
    padding: $space-4;
    @include custom-scrollbar;
  }
  
  .config-section {
    display: flex;
    flex-direction: column;
    gap: $space-5;
  }
</style>
