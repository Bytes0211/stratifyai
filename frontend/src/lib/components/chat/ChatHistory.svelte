<script lang="ts">
  import { chatStore } from '$lib/stores/chat';
  import { User, Bot, AlertCircle } from 'lucide-svelte';
  
  // Get last 15 messages (non-system)
  $: recentMessages = $chatStore.messages
    .filter(m => m.role !== 'system')
    .slice(-15);
  
  function truncate(text: string, maxLen: number = 80): string {
    if (text.length <= maxLen) return text;
    return text.slice(0, maxLen) + '...';
  }
  
  function formatTime(date: Date): string {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
</script>

<div class="chat-history">
  {#if recentMessages.length === 0}
    <div class="empty-state">
      <p>No messages yet</p>
      <p class="hint">Start a conversation to see history</p>
    </div>
  {:else}
    <div class="history-list">
      {#each recentMessages as message (message.id)}
        <div class="history-item" class:error={message.error}>
          <div class="item-header">
            {#if message.role === 'user'}
              <User size={14} class="icon user" />
              <span class="role user">You</span>
            {:else}
              {#if message.error}
                <AlertCircle size={14} class="icon error" />
              {:else}
                <Bot size={14} class="icon assistant" />
              {/if}
              <span class="role assistant">Assistant</span>
            {/if}
            <span class="time">{formatTime(message.timestamp)}</span>
          </div>
          <div class="item-content">
            {truncate(message.content)}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  
  .chat-history {
    height: 100%;
    display: flex;
    flex-direction: column;
  }
  
  .empty-state {
    text-align: center;
    padding: $space-8 $space-4;
    color: var(--text-muted);
    
    p {
      margin: 0;
    }
    
    .hint {
      font-size: $text-xs;
      margin-top: $space-2;
    }
  }
  
  .history-list {
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }
  
  .history-item {
    padding: $space-2 $space-3;
    background: var(--bg-elevated);
    border-radius: $radius-lg;
    font-size: $text-sm;
    
    &.error {
      border-left: 2px solid $error;
    }
  }
  
  .item-header {
    display: flex;
    align-items: center;
    gap: $space-2;
    margin-bottom: $space-1;
    
    :global(.icon) {
      flex-shrink: 0;
    }
    
    :global(.icon.user) {
      color: var(--accent);
    }
    
    :global(.icon.assistant) {
      color: $success;
    }
    
    :global(.icon.error) {
      color: $error;
    }
  }
  
  .role {
    font-weight: $font-medium;
    font-size: $text-xs;
    
    &.user {
      color: var(--accent);
    }
    
    &.assistant {
      color: $success;
    }
  }
  
  .time {
    margin-left: auto;
    font-size: $text-xs;
    color: var(--text-muted);
  }
  
  .item-content {
    color: var(--text-secondary);
    line-height: 1.4;
    word-break: break-word;
  }
</style>
