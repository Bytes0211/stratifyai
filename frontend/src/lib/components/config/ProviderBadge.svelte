<script lang="ts">
  import type { Provider } from '$lib/api/types';
  
  export let provider: Provider;
  export let size: 'sm' | 'md' = 'md';
  
  const providerLabels: Record<Provider, string> = {
    openai: 'OpenAI',
    anthropic: 'Anthropic',
    google: 'Google',
    deepseek: 'DeepSeek',
    groq: 'Groq',
    grok: 'Grok',
    openrouter: 'OpenRouter',
    ollama: 'Ollama',
    bedrock: 'AWS Bedrock',
  };
</script>

<span class="provider-badge {provider} {size}">
  {providerLabels[provider]}
</span>

<style lang="scss">
  @use '../../styles/tokens' as *;
  
  .provider-badge {
    display: inline-flex;
    align-items: center;
    font-weight: $font-medium;
    border-radius: $radius-full;
    
    &.sm {
      font-size: $text-xs;
      padding: 2px $space-2;
    }
    
    &.md {
      font-size: $text-xs;
      padding: $space-1 $space-2;
    }
    
    // Provider-specific colors
    &.openai {
      background: rgba($provider-openai, 0.15);
      color: $provider-openai;
    }
    
    &.anthropic {
      background: rgba($provider-anthropic, 0.15);
      color: $provider-anthropic;
    }
    
    &.google {
      background: rgba($provider-google, 0.15);
      color: $provider-google;
    }
    
    &.deepseek {
      background: rgba($provider-deepseek, 0.15);
      color: $provider-deepseek;
    }
    
    &.groq {
      background: rgba($provider-groq, 0.15);
      color: $provider-groq;
    }
    
    &.grok {
      background: rgba($provider-grok, 0.15);
      color: $provider-grok;
    }
    
    &.openrouter {
      background: rgba($provider-openrouter, 0.15);
      color: $provider-openrouter;
    }
    
    &.ollama {
      background: var(--bg-elevated);
      color: var(--text-primary);
      border: 1px solid var(--bg-hover);
    }
    
    &.bedrock {
      background: rgba($provider-bedrock, 0.15);
      color: $provider-bedrock;
    }
  }
</style>
