import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';

const mocks = vi.hoisted(() => {
  const { writable, derived } = require('svelte/store');

  const mockServers = writable([]);

  const mockMcpRuntimeStore = derived(mockServers, ($servers: any[]) => ({
    servers: $servers,
    tools: [],
    loading: false,
    error: null,
    initialized: true,
  }));

  return {
    mockServers,
    mockMcpRuntimeStore,
    mockRefresh: vi.fn(),
    mockEnsureLoaded: vi.fn(),
    mockStartServer: vi.fn(),
    mockStopServer: vi.fn(),
    mockRestartServer: vi.fn(),
    mockRemoveServer: vi.fn(),
    mockRemoveTool: vi.fn(),
    mockGetMcpCatalog: vi.fn(),
    mockGetMcpClients: vi.fn(),
    mockGetMcpStatus: vi.fn(),
    mockConfigureMcp: vi.fn(),
    mockConfigureCustomMcp: vi.fn(),
    mockResetMcpConfig: vi.fn(),
    mockGetMcpClientPermissions: vi.fn(),
    mockUpdateMcpClientPermissions: vi.fn(),
    mockUpdateCustomMcp: vi.fn(),
    mockDeleteCustomMcp: vi.fn(),
    mockExportCustomMcp: vi.fn(),
    mockImportCustomMcp: vi.fn(),
  };
});

vi.mock('$lib/stores/mcp', () => ({
  mcpRuntimeStore: mocks.mockMcpRuntimeStore,
  mcpRuntimeActions: {
    refresh: mocks.mockRefresh,
    ensureLoaded: mocks.mockEnsureLoaded,
    startServer: mocks.mockStartServer,
    stopServer: mocks.mockStopServer,
    restartServer: mocks.mockRestartServer,
    removeServer: mocks.mockRemoveServer,
    removeTool: mocks.mockRemoveTool,
  },
}));

vi.mock('$lib/api/client', () => ({
  getMcpCatalog: mocks.mockGetMcpCatalog,
  getMcpClients: mocks.mockGetMcpClients,
  getMcpStatus: mocks.mockGetMcpStatus,
  configureMcp: mocks.mockConfigureMcp,
  configureCustomMcp: mocks.mockConfigureCustomMcp,
  resetMcpConfig: mocks.mockResetMcpConfig,
  getMcpClientPermissions: mocks.mockGetMcpClientPermissions,
  updateMcpClientPermissions: mocks.mockUpdateMcpClientPermissions,
  updateCustomMcp: mocks.mockUpdateCustomMcp,
  deleteCustomMcp: mocks.mockDeleteCustomMcp,
  exportCustomMcp: mocks.mockExportCustomMcp,
  importCustomMcp: mocks.mockImportCustomMcp,
  getMcpClientServers: vi.fn().mockResolvedValue({ servers: [] }),
  getMcpClientTools: vi.fn().mockResolvedValue({ tools: [] }),
  startMcpClientServer: vi.fn(),
  stopMcpClientServer: vi.fn(),
  restartMcpClientServer: vi.fn(),
  getMcpClientHealth: vi.fn().mockResolvedValue({ healthy: true }),
  getMcpTools: vi.fn().mockResolvedValue({ tools: [] }),
  testMcpTool: vi.fn(),
  removeMcpClientTool: vi.fn(),
  getMcpClientResource: vi.fn(),
}));

import MCPServersPage from '$lib/components/mcp/MCPServersPage.svelte';

const CATALOG_RESPONSE = {
  servers: [
    {
      id: 'filesystem',
      name: 'Filesystem',
      description: 'Access local files',
      category: 'tools',
      install_method: 'npx',
      website: '',
      tags: ['files'],
      env_vars: [],
      user_args: [],
    },
  ],
};

const CLIENTS_RESPONSE = {
  clients: [
    { id: 'cursor', label: 'Cursor', config_path: '/home/.cursor/mcp.json', supports_apply: true },
  ],
};

const STATUS_RESPONSE = {
  client: 'cursor',
  path: '/home/.cursor/mcp.json',
  count: 0,
  configured: {},
};

const PERMISSIONS_RESPONSE = {
  client: 'cursor',
  path: '/home/.cursor/mcp.json',
  servers: {},
};

function setupDefaultMocks() {
  mocks.mockGetMcpCatalog.mockResolvedValue(CATALOG_RESPONSE);
  mocks.mockGetMcpClients.mockResolvedValue(CLIENTS_RESPONSE);
  mocks.mockGetMcpStatus.mockResolvedValue(STATUS_RESPONSE);
  mocks.mockGetMcpClientPermissions.mockResolvedValue(PERMISSIONS_RESPONSE);
  mocks.mockRefresh.mockResolvedValue(undefined);
}

describe('MCPServersPage – Phase 2 custom server form', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.mockServers.set([]);
    setupDefaultMocks();
  });

  it('renders Catalog and Add Custom tabs', async () => {
    render(MCPServersPage);
    // Wait for initialization to complete
    await vi.waitFor(() => {
      expect(screen.getByText('Catalog')).toBeInTheDocument();
    });
    expect(screen.getByText('Add Custom')).toBeInTheDocument();
  });

  it('shows catalog grid by default, not custom form', async () => {
    render(MCPServersPage);
    await vi.waitFor(() => {
      expect(screen.getByText('Filesystem')).toBeInTheDocument();
    });
    expect(screen.queryByText('Add Custom Server')).toBeNull();
  });

  it('switches to custom form when Add Custom tab is clicked', async () => {
    render(MCPServersPage);
    await vi.waitFor(() => {
      expect(screen.getByText('Add Custom')).toBeInTheDocument();
    });
    await fireEvent.click(screen.getByText('Add Custom'));
    expect(screen.getByText('Add Custom Server')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('my-custom-server')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g. node, python, npx')).toBeInTheDocument();
  });

  it('validates required fields on preview', async () => {
    render(MCPServersPage);
    await vi.waitFor(() => {
      expect(screen.getByText('Add Custom')).toBeInTheDocument();
    });
    await fireEvent.click(screen.getByText('Add Custom'));

    // Click Preview without filling in fields
    const previewButtons = screen.getAllByText('Preview config');
    await fireEvent.click(previewButtons[0]);

    expect(screen.getByText('Server ID is required.')).toBeInTheDocument();
    expect(screen.getByText('Command is required.')).toBeInTheDocument();
    expect(mocks.mockConfigureCustomMcp).not.toHaveBeenCalled();
  });

  it('calls configureCustomMcp with correct payload on preview', async () => {
    mocks.mockConfigureCustomMcp.mockResolvedValue({
      applied: false,
      config: { mcpServers: { 'my-server': { command: 'node' } } },
      commands: [],
      path: null,
      warnings: [],
    });

    render(MCPServersPage);
    await vi.waitFor(() => {
      expect(screen.getByText('Add Custom')).toBeInTheDocument();
    });
    await fireEvent.click(screen.getByText('Add Custom'));

    const serverIdInput = screen.getByPlaceholderText('my-custom-server');
    const commandInput = screen.getByPlaceholderText('e.g. node, python, npx');
    await fireEvent.input(serverIdInput, { target: { value: 'my-server' } });
    await fireEvent.input(commandInput, { target: { value: 'node' } });

    const previewButtons = screen.getAllByText('Preview config');
    await fireEvent.click(previewButtons[0]);

    expect(mocks.mockConfigureCustomMcp).toHaveBeenCalledWith(
      expect.objectContaining({
        server_id: 'my-server',
        command: 'node',
        client: 'cursor',
        apply: false,
      }),
    );
  });

  it('validates server_id format (lowercase, hyphens only)', async () => {
    render(MCPServersPage);
    await vi.waitFor(() => {
      expect(screen.getByText('Add Custom')).toBeInTheDocument();
    });
    await fireEvent.click(screen.getByText('Add Custom'));

    const serverIdInput = screen.getByPlaceholderText('my-custom-server');
    const commandInput = screen.getByPlaceholderText('e.g. node, python, npx');
    await fireEvent.input(serverIdInput, { target: { value: 'My Server' } });
    await fireEvent.input(commandInput, { target: { value: 'node' } });

    const previewButtons = screen.getAllByText('Preview config');
    await fireEvent.click(previewButtons[0]);

    expect(screen.getByText('Lowercase alphanumeric and hyphens only.')).toBeInTheDocument();
    expect(mocks.mockConfigureCustomMcp).not.toHaveBeenCalled();
  });
});
