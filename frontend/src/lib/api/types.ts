// ============================================
// API TYPES - Matches FastAPI backend models
// ============================================

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  provider: string;
  model: string;
  messages: Message[];
  temperature?: number;
  max_tokens?: number;
  stream?: boolean;
  file_content?: string;
  file_name?: string;
  chunked?: boolean;
  chunk_size?: number;
}

export interface UsageStats {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: number;
  latency_ms?: number;
}

export interface ChatResponse {
  id: string;
  provider: string;
  model: string;
  content: string;
  finish_reason: string;
  usage: UsageStats;
  cost_usd: number;
}

export interface ModelInfo {
  id: string;
  display_name: string;
  description: string;
  category: string;
  reasoning_model: boolean;
  supports_vision: boolean;
}

export interface ModelListResponse {
  models: ModelInfo[];
  validation: {
    validated: boolean;
    api_key_set: boolean;
    validation_time_ms: number;
    error: string | null;
  };
}

export interface CatalogModel {
  model_id: string;
  display_name: string;
  input_cost_per_1m: number;
  output_cost_per_1m: number;
  context_window: number;
  max_output_tokens: number;
  supports_vision: boolean;
  supports_tools: boolean;
  is_reasoning_model: boolean;
  category: string;
  description: string;
  deprecated?: boolean;
  deprecated_date?: string;
  replacement_model?: string;
}

export interface ProviderCatalog {
  [modelId: string]: CatalogModel;
}

export interface FullCatalog {
  [provider: string]: ProviderCatalog;
}

export interface CostSummary {
  total_cost: number;
  total_tokens: number;
  total_calls: number;
  cost_by_provider: Record<string, number>;
  cost_by_model: Record<string, number>;
  tokens_by_provider: Record<string, number>;
  cache_stats: {
    total_cache_read_tokens: number;
    total_cache_creation_tokens: number;
    cache_hit_rate_percent: number;
  };
  budget_status: {
    budget_set: boolean;
    total_cost: number;
    budget_limit?: number;
    remaining?: number;
    percent_used?: number;
    over_budget?: boolean;
    alert_threshold?: number;
  };
}

export interface StreamMessage {
  content?: string;
  done?: boolean;
  error?: string;
  usage?: UsageStats;
}

export type Provider = 
  | 'openai' 
  | 'anthropic' 
  | 'google' 
  | 'deepseek' 
  | 'groq' 
  | 'grok' 
  | 'openrouter' 
  | 'ollama' 
  | 'bedrock';

export const PROVIDERS: Provider[] = [
  'openai',
  'anthropic',
  'google',
  'deepseek',
  'groq',
  'grok',
  'openrouter',
  'ollama',
  'bedrock',
];

export const PROVIDER_COLORS: Record<Provider, string> = {
  openai: 'var(--provider-openai)',
  anthropic: 'var(--provider-anthropic)',
  google: 'var(--provider-google)',
  deepseek: 'var(--provider-deepseek)',
  groq: 'var(--provider-groq)',
  grok: 'var(--provider-grok)',
  openrouter: 'var(--provider-openrouter)',
  ollama: 'var(--provider-ollama)',
  bedrock: 'var(--provider-bedrock)',
};
