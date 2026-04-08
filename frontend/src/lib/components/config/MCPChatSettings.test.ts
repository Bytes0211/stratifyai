import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';

const mocks = vi.hoisted(() => {
  const { writable, derived } = require('svelte/store');

  const mockServers = writable([]);
  const mockActiveMcpServers = writable([]);
  const mockLoading = writable(false);

  const mockMcpRuntimeStore = derived(
    [mockServers, mockLoading],
    ([$servers, $loading]: [any[], boolean]) => ({
      servers: $servers,
      tools: [],
      loading: $loading,
      error: null,
      initialized: true,
    }),
  );

  const mockConfigStore = derived(mockActiveMcpServers, ($active: string[]) => ({
    activeMcpServers: $active,
    provider: 'openai',
    model: 'gpt-4o',
    temperature: 0.7,
    maxTokens: null,
    chunked: false,
    chunkSize: 50000,
    stream: true,
    modelInfo: null,
    isReasoningModel: false,
    supportsVision: false,
    effectiveTemperature: 0.7,
  }));

  return {
    mockServers,
    mockActiveMcpServers,
    mockLoading,
    mockMcpRuntimeStore,
    mockConfigStore,
  };
});

vi.mock('$lib/stores/mcp', () => ({
  mcpRuntimeStore: mocks.mockMcpRuntimeStore,
  mcpRuntimeActions: {
    ensureLoaded: vi.fn(),
    refresh: vi.fn(),
  },
}));

vi.mock('$lib/stores/config', () => ({
  configStore: mocks.mockConfigStore,
  configActions: {
    toggleActiveMcpServer: vi.fn(),
    setActiveMcpServers: vi.fn(),
  },
}));

import MCPChatSettings from '$lib/components/config/MCPChatSettings.svelte';

describe('MCPChatSettings (compact summary)', () => {
  beforeEach(() => {
    mocks.mockServers.set([]);
    mocks.mockActiveMcpServers.set([]);
    mocks.mockLoading.set(false);
  });

  it('shows "not configured" when no servers exist', () => {
    render(MCPChatSettings);
    expect(screen.getByText('MCP Tools: not configured')).toBeInTheDocument();
  });

  it('shows "none active" when servers exist but none selected', () => {
    mocks.mockServers.set([
      { server_id: 'postgres', enabled: true, status: 'connected', tool_count: 1, tools: ['query'] },
    ]);
    render(MCPChatSettings);
    expect(screen.getByText('MCP Tools: none active')).toBeInTheDocument();
  });

  it('shows active count with strong emphasis', () => {
    mocks.mockServers.set([
      { server_id: 'postgres', enabled: true, status: 'connected', tool_count: 1, tools: ['query'] },
      { server_id: 'brave', enabled: true, status: 'connected', tool_count: 2, tools: ['search'] },
    ]);
    mocks.mockActiveMcpServers.set(['postgres', 'brave']);
    render(MCPChatSettings);
    expect(screen.getByText('2 active')).toBeInTheDocument();
  });

  it('shows active server names (up to 3)', () => {
    mocks.mockServers.set([
      { server_id: 'a', enabled: true, status: 'connected', tool_count: 1, tools: [] },
      { server_id: 'b', enabled: true, status: 'connected', tool_count: 1, tools: [] },
    ]);
    mocks.mockActiveMcpServers.set(['a', 'b']);
    render(MCPChatSettings);
    expect(screen.getByText('a, b')).toBeInTheDocument();
  });

  it('shows overflow indicator when > 3 servers active', () => {
    mocks.mockServers.set([
      { server_id: 'a', enabled: true, status: 'connected', tool_count: 1, tools: [] },
      { server_id: 'b', enabled: true, status: 'connected', tool_count: 1, tools: [] },
      { server_id: 'c', enabled: true, status: 'connected', tool_count: 1, tools: [] },
      { server_id: 'd', enabled: true, status: 'connected', tool_count: 1, tools: [] },
    ]);
    mocks.mockActiveMcpServers.set(['a', 'b', 'c', 'd']);
    render(MCPChatSettings);
    expect(screen.getByText('a, b, c +1')).toBeInTheDocument();
  });

  it('shows "Manage" hint when servers are available', () => {
    mocks.mockServers.set([
      { server_id: 'test', enabled: true, status: 'connected', tool_count: 0, tools: [] },
    ]);
    render(MCPChatSettings);
    expect(screen.getByText('Manage servers in the panel below the chat')).toBeInTheDocument();
  });

  it('does not show hint when no servers available', () => {
    render(MCPChatSettings);
    expect(screen.queryByText('Manage servers in the panel below the chat')).toBeNull();
  });

  it('shows loading state', () => {
    mocks.mockLoading.set(true);
    render(MCPChatSettings);
    expect(screen.getByText(/loading/)).toBeInTheDocument();
  });
});
