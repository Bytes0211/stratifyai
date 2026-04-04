// ============================================
// HTTP CLIENT - REST API wrapper
// ============================================

import type { 
  ChatRequest, 
  ChatResponse, 
  ModelListResponse, 
  FullCatalog,
  CostSummary,
  Provider,
  McpCatalogResponse,
  McpClientsResponse,
  McpStatusResponse,
  McpConfigureRequest,
  McpConfigureResponse
} from './types';

const API_BASE = '/api';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(
      error.error || `HTTP ${response.status}`,
      response.status,
      error.detail
    );
  }
  
  return response.json();
}

// ============================================
// API METHODS
// ============================================

export async function getProviders(): Promise<string[]> {
  return request<string[]>('/providers');
}

export async function getModels(provider: Provider): Promise<ModelListResponse> {
  return request<ModelListResponse>(`/models/${provider}`);
}

export async function getAllModels(): Promise<FullCatalog> {
  return request<FullCatalog>('/all-models');
}

export async function getCatalog(): Promise<FullCatalog> {
  return request<FullCatalog>('/catalog');
}

export async function chat(req: ChatRequest): Promise<ChatResponse> {
  return request<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export async function getCosts(): Promise<CostSummary> {
  return request<CostSummary>('/cost');
}

export async function getHealth(): Promise<{ status: string; version: string }> {
  return request<{ status: string; version: string }>('/health');
}

export async function getMcpCatalog(): Promise<McpCatalogResponse> {
  return request<McpCatalogResponse>('/mcp/catalog');
}

export async function getMcpClients(projectRoot?: string): Promise<McpClientsResponse> {
  const query = projectRoot ? `?project_root=${encodeURIComponent(projectRoot)}` : '';
  return request<McpClientsResponse>(`/mcp/clients${query}`);
}

export async function getMcpStatus(
  client: McpConfigureRequest['client'],
  projectRoot?: string
): Promise<McpStatusResponse> {
  const params = new URLSearchParams({ client });
  if (projectRoot) {
    params.set('project_root', projectRoot);
  }
  return request<McpStatusResponse>(`/mcp/status?${params.toString()}`);
}

export async function configureMcp(req: McpConfigureRequest): Promise<McpConfigureResponse> {
  return request<McpConfigureResponse>('/mcp/configure', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export { ApiError };
