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
  McpConfigureResponse,
  McpToolsResponse,
  McpToolTestRequest,
  McpToolTestResponse,
  McpClientServersResponse,
  McpClientToolsResponse,
  McpClientToolExecuteResponse,
  McpClientResourceResponse,
  McpClientHealthResponse,
  McpClientPermissionsResponse,
  McpClientPermissionsUpdateRequest
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

export async function getMcpClientServers(): Promise<McpClientServersResponse> {
  return request<McpClientServersResponse>('/mcp-client/servers');
}

export async function startMcpClientServer(serverId: string): Promise<{ server_id: string; status: string; error?: string | null }> {
  return request(`/mcp-client/servers/${encodeURIComponent(serverId)}/start`, {
    method: 'POST',
  });
}

export async function stopMcpClientServer(serverId: string): Promise<{ server_id: string; status: string; error?: string | null }> {
  return request(`/mcp-client/servers/${encodeURIComponent(serverId)}/stop`, {
    method: 'POST',
  });
}

export async function restartMcpClientServer(serverId: string): Promise<{ server_id: string; status: string; error?: string | null }> {
  return request(`/mcp-client/servers/${encodeURIComponent(serverId)}/restart`, {
    method: 'POST',
  });
}

export async function getMcpClientTools(): Promise<McpClientToolsResponse> {
  return request<McpClientToolsResponse>('/mcp-client/tools');
}

export async function executeMcpClientTool(
  serverId: string,
  toolName: string,
  payload: Record<string, unknown> = {}
): Promise<McpClientToolExecuteResponse> {
  return request<McpClientToolExecuteResponse>(
    `/mcp-client/tools/${encodeURIComponent(serverId)}/${encodeURIComponent(toolName)}`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
    }
  );
}

export async function getMcpClientResource(
  serverId: string,
  uri: string
): Promise<McpClientResourceResponse> {
  return request<McpClientResourceResponse>(
    `/mcp-client/resources/${encodeURIComponent(serverId)}/${encodeURIComponent(uri)}`
  );
}

export async function getMcpClientHealth(): Promise<McpClientHealthResponse> {
  return request<McpClientHealthResponse>('/mcp-client/health');
}

export async function getMcpClientPermissions(
  client: McpConfigureRequest['client'],
  projectRoot?: string,
  outputPath?: string
): Promise<McpClientPermissionsResponse> {
  const params = new URLSearchParams({ client });
  if (projectRoot) {
    params.set('project_root', projectRoot);
  }
  if (outputPath) {
    params.set('output_path', outputPath);
  }
  return request<McpClientPermissionsResponse>(`/mcp-client/permissions?${params.toString()}`);
}

export async function updateMcpClientPermissions(
  req: McpClientPermissionsUpdateRequest
): Promise<McpClientPermissionsResponse> {
  return request<McpClientPermissionsResponse>('/mcp-client/permissions', {
    method: 'PUT',
    body: JSON.stringify(req),
  });
}

export async function getMcpTools(): Promise<McpToolsResponse> {
  return request<McpToolsResponse>('/mcp/tools');
}

export async function testMcpTool(req: McpToolTestRequest): Promise<McpToolTestResponse> {
  return request<McpToolTestResponse>('/mcp/test-tool', {
    method: 'POST',
    body: JSON.stringify(req),
  });
}

export { ApiError };
