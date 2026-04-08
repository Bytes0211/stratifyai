import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';

const mocks = vi.hoisted(() => {
  const { writable, derived } = require('svelte/store');

  const mockServers = writable([]);
  const mockActiveMcpServers = writable([]);

  const mockMcpRuntimeStore = derived(mockServers, ($servers: any[]) => ({
    servers: $servers,
    tools: [],
    loading: false,
    error: null,
    initialized: true,
  }));

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
    mockMcpRuntimeStore,
    mockConfigStore,
    mockRefresh: vi.fn(),
    mockEnsureLoaded: vi.fn(),
    mockToggleActiveMcpServer: vi.fn(),
    mockRemoveServer: vi.fn(),
  };
});

vi.mock('$lib/stores/mcp', () => ({
  mcpRuntimeStore: mocks.mockMcpRuntimeStore,
  mcpRuntimeActions: {
    refresh: mocks.mockRefresh,
    ensureLoaded: mocks.mockEnsureLoaded,
    removeServer: mocks.mockRemoveServer,
  },
}));

vi.mock('$lib/stores/config', () => ({
  configStore: mocks.mockConfigStore,
  configActions: {
    toggleActiveMcpServer: mocks.mockToggleActiveMcpServer,
    setActiveMcpServers: vi.fn(),
  },
}));

import MCPChatPanel from '$lib/components/chat/MCPChatPanel.svelte';

describe('MCPChatPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.mockServers.set([]);
    mocks.mockActiveMcpServers.set([]);
  });

  it('does not render when no servers available', () => {
    const { container } = render(MCPChatPanel);
    expect(container.querySelector('.mcp-chat-panel')).toBeNull();
  });

  it('shows "none active" when servers exist but none selected', () => {
    mocks.mockServers.set([
      { server_id: 'postgres', enabled: true, status: 'connected', tool_count: 1, tools: ['query'] },
    ]);
    render(MCPChatPanel);
    expect(screen.getByText('MCP Tools: none active')).toBeInTheDocument();
  });

  it('shows active count when servers are selected', () => {
    mocks.mockServers.set([
      { server_id: 'postgres', enabled: true, status: 'connected', tool_count: 1, tools: ['query'] },
      { server_id: 'brave', enabled: true, status: 'connected', tool_count: 2, tools: ['brave_search', 'brave_news'] },
    ]);
    mocks.mockActiveMcpServers.set(['postgres', 'brave']);
    render(MCPChatPanel);
    expect(screen.getByText('MCP Tools: 2 active')).toBeInTheDocument();
  });

  it('starts collapsed and expands on click', async () => {
    mocks.mockServers.set([
      { server_id: 'postgres', enabled: true, status: 'connected', tool_count: 1, tools: ['query'] },
    ]);
    render(MCPChatPanel);

    // Panel body should not be visible initially
    expect(screen.queryByText('1 tool')).toBeNull();

    // Click the toggle to expand
    const toggle = screen.getByRole('button', { expanded: false });
    await fireEvent.click(toggle);

    // Server details should now be visible
    expect(screen.getByText('1 tool')).toBeInTheDocument();
    expect(screen.getByText('postgres')).toBeInTheDocument();
  });

  it('calls ensureLoaded on mount', () => {
    mocks.mockServers.set([
      { server_id: 'test', enabled: true, status: 'connected', tool_count: 0, tools: [] },
    ]);
    render(MCPChatPanel);
    expect(mocks.mockEnsureLoaded).toHaveBeenCalled();
  });

  it('toggles a server when checkbox is clicked', async () => {
    mocks.mockServers.set([
      { server_id: 'postgres', enabled: true, status: 'connected', tool_count: 1, tools: ['query'] },
    ]);
    render(MCPChatPanel);

    // Expand first
    const toggle = screen.getByRole('button', { expanded: false });
    await fireEvent.click(toggle);

    // Click the checkbox
    const checkbox = screen.getByRole('checkbox');
    await fireEvent.click(checkbox);
    expect(mocks.mockToggleActiveMcpServer).toHaveBeenCalledWith('postgres');
  });

  it('shows tool names in expanded view (up to 3)', async () => {
    mocks.mockServers.set([
      { server_id: 'brave', enabled: true, status: 'connected', tool_count: 4, tools: ['search', 'news', 'images', 'videos'] },
    ]);
    render(MCPChatPanel);

    const toggle = screen.getByRole('button', { expanded: false });
    await fireEvent.click(toggle);

    expect(screen.getByText(/search • news • images/)).toBeInTheDocument();
  });

  it('shows selection summary when servers are active and panel expanded', async () => {
    mocks.mockServers.set([
      { server_id: 'postgres', enabled: true, status: 'connected', tool_count: 1, tools: ['query'] },
    ]);
    mocks.mockActiveMcpServers.set(['postgres']);
    render(MCPChatPanel);

    const toggle = screen.getByRole('button', { expanded: false });
    await fireEvent.click(toggle);

    expect(screen.getByText(/Active: postgres/)).toBeInTheDocument();
  });

  it('disables checkbox for error-status servers', async () => {
    mocks.mockServers.set([
      { server_id: 'broken', enabled: true, status: 'error', tool_count: 0, tools: [] },
    ]);
    render(MCPChatPanel);

    const toggle = screen.getByRole('button', { expanded: false });
    await fireEvent.click(toggle);

    const checkbox = screen.getByRole('checkbox');
    expect(checkbox).toBeDisabled();
  });
});
