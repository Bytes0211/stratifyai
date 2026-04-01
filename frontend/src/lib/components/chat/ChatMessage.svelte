<script lang="ts">
  import type { ChatMessage } from '$lib/stores/chat';
  import MarkdownRenderer from './MarkdownRenderer.svelte';
  import { User, Bot, AlertCircle } from 'lucide-svelte';
  
  export let message: ChatMessage;
  
  function formatCost(cost: number): string {
    if (cost < 0.001) {
      return `$${cost.toFixed(6)}`;
    }
    return `$${cost.toFixed(4)}`;
  }
  
  function formatTokens(tokens: number): string {
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}k`;
    }
    return tokens.toString();
  }
  
  function formatLatency(ms: number): string {
    if (ms >= 1000) {
      return `${(ms / 1000).toFixed(2)}s`;
    }
    return `${Math.round(ms)}ms`;
  }
</script>

<div class="message {message.role}" class:error={message.error}>
  <div class="message-avatar">
    {#if message.role === 'user'}
      <User size={18} />
    {:else if message.error}
      <AlertCircle size={18} />
    {:else}
      <Bot size={18} />
    {/if}
  </div>
  
  <div class="message-content">
    <div class="message-header">
      <span class="message-role">
        {#if message.role === 'user'}
          You
        {:else if message.role === 'system'}
          System
        {:else}
          Assistant
        {/if}
      </span>
      {#if message.usage}
        <span class="message-meta">
          {formatTokens(message.usage.total_tokens)} tokens • {formatCost(message.usage.cost_usd)}
          {#if typeof message.usage.latency_ms === 'number' && message.usage.latency_ms > 0}
            <span class="latency"> • {formatLatency(message.usage.latency_ms)}</span>
          {/if}
        </span>
      {/if}
    </div>
    
    <div class="message-body">
      {#if message.role === 'assistant' && !message.error}
        <MarkdownRenderer content={message.content} />
      {:else}
        <p>{message.content}</p>
      {/if}
    </div>
  </div>
</div>

<style lang="scss">
  @use '../../styles/tokens' as *;
  @use '../../styles/mixins' as *;
  
  .message {
    display: flex;
    gap: $space-3;
    animation: fadeIn 0.2s ease-out;
  }
  
  @keyframes fadeIn {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .message-avatar {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: $radius-lg;
    background: var(--bg-elevated);
    color: var(--text-secondary);
    
    .user & {
      background: var(--accent);
      color: #0f172a;
    }
    
    .error & {
      background: rgba($error, 0.15);
      color: $error;
    }
  }
  
  .message-content {
    flex: 1;
    min-width: 0;
  }
  
  .message-header {
    display: flex;
    align-items: center;
    gap: $space-3;
    margin-bottom: $space-1;
  }
  
  .message-role {
    font-size: $text-sm;
    font-weight: $font-semibold;
    color: var(--text-primary);
    
    .user & {
      color: var(--accent);
    }
    
    .error & {
      color: $error;
    }
  }
  
  .message-meta {
    font-size: $text-xs;
    color: var(--text-muted);
  }
  
  .message-body {
    font-size: $text-sm;
    line-height: $leading-relaxed;
    color: var(--text-primary);
    
    p {
      margin: 0;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
    
    .error & {
      color: $error;
    }
  }
</style>
