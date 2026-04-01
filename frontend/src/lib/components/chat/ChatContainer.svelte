<script lang="ts">
  import { afterUpdate } from 'svelte';
  import ChatMessage from './ChatMessage.svelte';
  import StreamingIndicator from './StreamingIndicator.svelte';
  import { chatStore } from '$lib/stores/chat';
  import { MessageSquare } from 'lucide-svelte';
  
  let containerRef: HTMLElement;
  
  // Auto-scroll to bottom when new messages arrive or streaming content updates
  afterUpdate(() => {
    if (containerRef) {
      containerRef.scrollTop = containerRef.scrollHeight;
    }
  });
</script>

<div class="chat-container" bind:this={containerRef} role="log" aria-live="polite">
  {#if !$chatStore.hasMessages && !$chatStore.isStreaming}
    <div class="empty-state">
      <div class="empty-icon">
        <MessageSquare size={48} />
      </div>
      <h2>Start a conversation</h2>
      <p>Select a model from the sidebar and type your message below.</p>
    </div>
  {:else}
    <div class="messages">
      {#each $chatStore.messages as message (message.id)}
        <ChatMessage {message} />
      {/each}
      
      {#if $chatStore.isStreaming}
        <div class="streaming-message">
          <ChatMessage 
            message={{
              id: $chatStore.streamingMessageId || 'streaming',
              role: 'assistant',
              content: $chatStore.streamingContent,
              timestamp: new Date(),
            }} 
          />
          <StreamingIndicator />
        </div>
      {/if}
    </div>
  {/if}
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .chat-container {
    flex: 1;
    overflow-y: auto;
    padding: $space-4;
    background: var(--bg-base);
    border-radius: $radius-xl;
    border: 1px solid var(--bg-elevated);
    @include custom-scrollbar;
  }
  
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 300px;
    text-align: center;
    color: var(--text-secondary);
    
    .empty-icon {
      color: var(--text-muted);
      margin-bottom: $space-4;
      opacity: 0.5;
    }
    
    h2 {
      font-size: $text-lg;
      color: var(--text-primary);
      margin-bottom: $space-2;
    }
    
    p {
      font-size: $text-sm;
      max-width: 300px;
    }
  }
  
  .messages {
    display: flex;
    flex-direction: column;
    gap: $space-4;
  }
  
  .streaming-message {
    position: relative;
  }
</style>
