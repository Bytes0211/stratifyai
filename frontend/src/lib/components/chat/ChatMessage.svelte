<script lang="ts">
  import type { ChatMessage } from '$lib/stores/chat';
  import MarkdownRenderer from './MarkdownRenderer.svelte';
  import { User, Bot, AlertCircle, ShieldCheck, TriangleAlert, Wrench } from 'lucide-svelte';
  
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

  function stringifyValue(value: unknown): string {
    if (typeof value === 'string') {
      return value;
    }
    return JSON.stringify(value, null, 2);
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

    {#if message.role === 'assistant' && ((message.activeMcpServers?.length ?? 0) > 0 || (message.toolResults?.length ?? 0) > 0 || (message.warnings?.length ?? 0) > 0)}
      <div class="mcp-panel">
        {#if message.activeMcpServers?.length}
          <div class="badge-row">
            <span class="badge info">
              <ShieldCheck size={12} />
              MCP enabled: {message.activeMcpServers.join(', ')}
            </span>
          </div>
        {/if}

        {#if message.toolResults?.length}
          <div class="badge-row">
            {#each message.toolResults as result, index}
              <span class:warning={Boolean(result.error)} class="badge tool">
                <Wrench size={12} />
                {String(result.namespace ?? result.tool_name ?? `tool-${index + 1}`)}
              </span>
            {/each}
          </div>

          <details class="tool-details">
            <summary>View MCP tool details</summary>
            <div class="tool-results-list">
              {#each message.toolResults as result, index}
                <article class="tool-result-card">
                  <div class="tool-result-header">
                    <strong>{String(result.namespace ?? result.tool_name ?? `tool-${index + 1}`)}</strong>
                    {#if typeof result.latency_ms === 'number'}
                      <span>{formatLatency(Number(result.latency_ms))}</span>
                    {/if}
                  </div>
                  {#if result.error}
                    <p class="warning-text">{String(result.error)}</p>
                  {:else}
                    <pre>{stringifyValue(result.result ?? result)}</pre>
                  {/if}
                </article>
              {/each}
            </div>
          </details>
        {/if}

        {#if message.warnings?.length}
          <div class="warnings-list">
            {#each message.warnings as warning}
              <span class="badge warning">
                <TriangleAlert size={12} />
                {warning}
              </span>
            {/each}
          </div>
        {/if}
      </div>
    {/if}
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

  .mcp-panel {
    margin-top: $space-3;
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }

  .badge-row,
  .warnings-list {
    display: flex;
    flex-wrap: wrap;
    gap: $space-2;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    gap: $space-1;
    padding: 2px $space-2;
    border-radius: 999px;
    font-size: $text-xs;
    background: var(--bg-elevated);
    color: var(--text-secondary);

    &.info {
      color: var(--accent);
    }

    &.warning {
      color: #f59e0b;
    }

    &.tool.warning {
      color: #ef4444;
    }
  }

  .tool-details {
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-lg;
    padding: $space-2 $space-3;
    background: var(--bg-surface);

    summary {
      cursor: pointer;
      color: var(--text-secondary);
      font-size: $text-xs;
    }
  }

  .tool-results-list {
    display: flex;
    flex-direction: column;
    gap: $space-2;
    margin-top: $space-2;
  }

  .tool-result-card {
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-md;
    padding: $space-2;
    background: var(--bg-base);

    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: $text-xs;
      color: var(--text-secondary);
    }
  }

  .tool-result-header {
    display: flex;
    justify-content: space-between;
    gap: $space-2;
    margin-bottom: $space-1;

    strong {
      color: var(--text-primary);
      font-size: $text-xs;
    }

    span {
      color: var(--text-muted);
      font-size: $text-xs;
    }
  }

  .warning-text {
    margin: 0;
    color: #f59e0b;
    font-size: $text-xs;
  }
</style>
