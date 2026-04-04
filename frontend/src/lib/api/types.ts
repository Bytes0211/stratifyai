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

export interface McpEnvVar {
  name: string;
  description: string;
  required: boolean;
  signup_url?: string | null;
  secret?: boolean;
}

export interface McpUserArg {
  name: string;
  description: string;
  required: boolean;
  flag?: string | null;
  example?: string | null;
  multiple?: boolean;
}

export interface McpServerEntry {
  id: string;
  name: string;
  description: string;
  category: string;
  website?: string | null;
  install_method: string;
  command: string;
  args: string[];
  env_vars: McpEnvVar[];
  user_args: McpUserArg[];
  tags: string[];
}

export interface McpCatalogResponse {
  version: string;
  updated: string;
  servers: McpServerEntry[];
}

export interface McpClientInfo {
  id: 'claude-desktop' | 'claude-code' | 'cursor' | 'vscode';
  label: string;
  config_path?: string | null;
  supports_apply: boolean;
  exists: boolean;
}

export interface McpClientsResponse {
  clients: McpClientInfo[];
}

export interface McpStatusResponse {
  client: string;
  path?: string | null;
  configured: Record<string, {
    command: string;
    args?: string[];
    env?: Record<string, string>;
  }>;
  count: number;
}

export interface McpConfigureRequest {
  client: 'claude-desktop' | 'claude-code' | 'cursor' | 'vscode';
  server_ids: string[];
  env_values?: Record<string, string>;
  arg_values?: Record<string, string>;
  project_root?: string;
  output_path?: string;
  apply?: boolean;
}

export interface McpConfigureResponse {
  applied: boolean;
  config: Record<string, unknown> | null;
  commands: string[];
  path?: string | null;
  warnings: string[];
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
