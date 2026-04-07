// ============================================
// MCP RUNTIME STORE - Shared server/tool state
// ============================================

import { get, writable } from 'svelte/store';

import {
  getMcpClientServers,
  getMcpClientTools,
  removeMcpClientTool,
  resetMcpConfig,
  restartMcpClientServer,
  startMcpClientServer,
  stopMcpClientServer,
} from '$lib/api/client';
import type {
  McpClientServerInfo,
  McpClientToolInfo,
  McpConfigureRequest,
} from '$lib/api/types';
import { configActions, configStore } from './config';

interface McpRuntimeState {
  servers: McpClientServerInfo[];
  tools: McpClientToolInfo[];
  loading: boolean;
  error: string | null;
  initialized: boolean;
}

const initialState: McpRuntimeState = {
  servers: [],
  tools: [],
  loading: false,
  error: null,
  initialized: false,
};

const PERSISTENT_REMOVE_CLIENTS: Array<McpConfigureRequest['client']> = [
  'claude-desktop',
  'cursor',
  'vscode',
];

function createMcpRuntimeStore() {
  const { subscribe, update } = writable<McpRuntimeState>(initialState);

  function setLoading(loading: boolean) {
    update((state) => ({ ...state, loading }));
  }

  function setError(error: string | null) {
    update((state) => ({ ...state, error }));
  }

  function pruneActiveChatServers(servers: McpClientServerInfo[]) {
    const availableServerIds = servers
      .filter((server) => server.enabled && server.status !== 'disabled')
      .map((server) => server.server_id);
    const availableIds = new Set(availableServerIds);

    const currentSelection = get(configStore).activeMcpServers;

    if (currentSelection.length === 0) {
      return;
    }

    const filtered = currentSelection.filter((serverId) => availableIds.has(serverId));
    if (filtered.length !== currentSelection.length) {
      configActions.setActiveMcpServers(filtered);
    }
  }

  async function refresh(forceRefresh = true) {
    try {
      setLoading(true);
      setError(null);

      const [serversResponse, toolsResponse] = await Promise.all([
        getMcpClientServers(forceRefresh),
        getMcpClientTools(forceRefresh),
      ]);

      pruneActiveChatServers(serversResponse.servers);
      update((state) => ({
        ...state,
        servers: serversResponse.servers,
        tools: toolsResponse.tools,
        error: null,
        initialized: true,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load live MCP client data';
      update((state) => ({
        ...state,
        error: message,
        initialized: true,
      }));
    } finally {
      setLoading(false);
    }
  }

  async function ensureLoaded() {
    const state = get({ subscribe });
    if (!state.initialized && !state.loading) {
      await refresh(true);
    }
  }

  async function startServer(serverId: string) {
    try {
      setError(null);
      await startMcpClientServer(serverId);
      await refresh(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : `Failed to start ${serverId}`;
      setError(message);
      throw err;
    }
  }

  async function stopServer(serverId: string) {
    try {
      setError(null);
      await stopMcpClientServer(serverId);
      await refresh(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : `Failed to stop ${serverId}`;
      setError(message);
      throw err;
    }
  }

  async function restartServer(serverId: string) {
    try {
      setError(null);
      await restartMcpClientServer(serverId);
      await refresh(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : `Failed to restart ${serverId}`;
      setError(message);
      throw err;
    }
  }

  async function removeServer(
    serverId: string,
    options?: {
      client?: McpConfigureRequest['client'];
      projectRoot?: string;
    }
  ) {
    try {
      setError(null);

      const state = get({ subscribe });
      const server = state.servers.find((item) => item.server_id === serverId);
      const sourceClient = server?.source_client as McpConfigureRequest['client'] | undefined;
      const orderedClients = Array.from(
        new Set(
          [options?.client, sourceClient, ...PERSISTENT_REMOVE_CLIENTS].filter(
            (value): value is McpConfigureRequest['client'] => Boolean(value)
          )
        )
      );

      let removedCount = 0;
      for (const client of orderedClients) {
        const result = await resetMcpConfig({
          client,
          server_ids: [serverId],
          project_root: options?.projectRoot,
        });
        removedCount += result.count;
      }

      if (removedCount == 0) {
        await stopMcpClientServer(serverId);
      }

      await refresh(true);
    } catch (err) {
      const message = err instanceof Error ? err.message : `Failed to remove ${serverId}`;
      setError(message);
      throw err;
    }
  }

  async function removeTool(serverId: string, toolName: string) {
    try {
      setError(null);
      await removeMcpClientTool(serverId, toolName);
      update((state) => {
        const tools = state.tools.filter(
          (tool) => !(tool.server_id === serverId && tool.name === toolName)
        );
        const servers = state.servers.map((server) => {
          if (server.server_id !== serverId) {
            return server;
          }
          const serverTools = tools
            .filter((tool) => tool.server_id === serverId)
            .map((tool) => tool.namespace);
          return {
            ...server,
            tool_count: serverTools.length,
            tools: serverTools,
          };
        });
        return {
          ...state,
          servers,
          tools,
        };
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : `Failed to remove tool ${toolName}`;
      setError(message);
      throw err;
    }
  }

  function clearError() {
    setError(null);
  }

  return {
    subscribe,
    refresh,
    ensureLoaded,
    startServer,
    stopServer,
    restartServer,
    removeServer,
    removeTool,
    clearError,
  };
}

export const mcpRuntimeStore = createMcpRuntimeStore();
export const mcpRuntimeActions = {
  refresh: (forceRefresh = true) => mcpRuntimeStore.refresh(forceRefresh),
  ensureLoaded: () => mcpRuntimeStore.ensureLoaded(),
  startServer: (serverId: string) => mcpRuntimeStore.startServer(serverId),
  stopServer: (serverId: string) => mcpRuntimeStore.stopServer(serverId),
  restartServer: (serverId: string) => mcpRuntimeStore.restartServer(serverId),
  removeServer: (
    serverId: string,
    options?: { client?: McpConfigureRequest['client']; projectRoot?: string }
  ) => mcpRuntimeStore.removeServer(serverId, options),
  removeTool: (serverId: string, toolName: string) =>
    mcpRuntimeStore.removeTool(serverId, toolName),
  clearError: () => mcpRuntimeStore.clearError(),
};
