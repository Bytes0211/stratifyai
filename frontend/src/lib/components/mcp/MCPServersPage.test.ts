import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';

// ---------------------------------------------------------------------------
// Hoisted mocks — values referenced inside vi.mock() factories
// ---------------------------------------------------------------------------
const mocks = vi.hoisted(() => {
  const { writable, derived } = require('svelte/store');

  const mockServers = writable([]);
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

  return {
    mockServers,
    mockLoading,
    mockMcpRuntimeStore,
    mockGetMcpCatalog: vi.fn(),
    mockGetMcpClients: vi.fn(),
    mockGetMcpStatus: vi.fn(),
    mockGetMcpClientPermissions: vi.fn(),
    mockConfigureMcp: vi.fn(),
    mockConfigureCustomMcp: vi.fn(),
    mockResetMcpConfig: vi.fn(),
    mockUpdateMcpClientPermissions: vi.fn(),
    mockRefresh: vi.fn(),
  };
});

// ---------------------------------------------------------------------------
// Module mocks
// ---------------------------------------------------------------------------
vi.mock('$lib/api/client', () => ({
  getMcpCatalog: mocks.mockGetMcpCatalog,
  getMcpClients: mocks.mockGetMcpClients,
  getMcpStatus: mocks.mockGetMcpStatus,
  getMcpClientPermissions: mocks.mockGetMcpClientPermissions,
  configureMcp: mocks.mockConfigureMcp,
  configureCustomMcp: mocks.mockConfigureCustomMcp,
  resetMcpConfig: mocks.mockResetMcpConfig,
  updateMcpClientPermissions: mocks.mockUpdateMcpClientPermissions,
  // Also needed by MCPToolTester (child component, rendered even if not tested)
  getMcpTools: vi.fn().mockResolvedValue({ tools: [] }),
  testMcpTool: vi.fn(),
}));

vi.mock('$lib/stores/mcp', () => ({
  mcpRuntimeStore: mocks.mockMcpRuntimeStore,
  mcpRuntimeActions: {
    refresh: mocks.mockRefresh,
    ensureLoaded: vi.fn(),
    startServer: vi.fn(),
    stopServer: vi.fn(),
    restartServer: vi.fn(),
    removeServer: vi.fn(),
    removeTool: vi.fn(),
    clearError: vi.fn(),
  },
}));

// MCPToolTester has its own heavy dependencies — stub it with a no-op Svelte 5 component.
vi.mock('./MCPToolTester.svelte', () => ({
  default: function MCPToolTester() {},
}));

import MCPServersPage from './MCPServersPage.svelte';

// ---------------------------------------------------------------------------
// Shared fixtures
// ---------------------------------------------------------------------------
const CATALOG_RESPONSE = {
  version: '1.0',
  updated: '2026-01-01',
  servers: [
    {
      id: 'brave-search',
      name: 'Brave Search',
      description: 'Web search via Brave',
      category: 'search',
      website: 'https://brave.com',
      install_method: 'npx',
      command: 'npx',
      args: ['-y', '@anthropic/mcp-brave-search'],
      env_vars: [],
      user_args: [],
      tags: ['search'],
    },
  ],
};

const CLIENTS_RESPONSE = {
  clients: [
    {
      id: 'cursor',
      label: 'Cursor',
      config_path: '/home/user/.cursor/mcp.json',
      supports_apply: true,
      exists: true,
    },
  ],
};

const STATUS_RESPONSE = {
  client: 'cursor',
  path: '/home/user/.cursor/mcp.json',
  configured: {},
  settings: {},
  count: 0,
};

const PERMISSIONS_RESPONSE = {
  client: 'cursor',
  path: '/home/user/.cursor/mcp.json',
  servers: {},
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Set up default mock return values so onMount succeeds and the loading state clears. */
function setupDefaultMocks() {
  mocks.mockGetMcpCatalog.mockResolvedValue(CATALOG_RESPONSE);
  mocks.mockGetMcpClients.mockResolvedValue(CLIENTS_RESPONSE);
  mocks.mockGetMcpStatus.mockResolvedValue(STATUS_RESPONSE);
  mocks.mockGetMcpClientPermissions.mockResolvedValue(PERMISSIONS_RESPONSE);
  mocks.mockRefresh.mockResolvedValue(undefined);
}

/** Render the page and wait until the loading spinner is gone. */
async function renderPage() {
  const result = render(MCPServersPage);
  await waitFor(() => {
    expect(screen.queryByText('Loading MCP catalog and client status...')).toBeNull();
  });
  return result;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
describe('MCPServersPage — Phase 2 (Custom Server Form)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.mockServers.set([]);
    mocks.mockLoading.set(false);
    setupDefaultMocks();
  });

  // =========================================================================
  // Tab toggle
  // =========================================================================
  describe('tab toggle', () => {
    it('defaults to catalog view with the Catalog tab active', async () => {
      await renderPage();
      expect(screen.getByText('Catalog Browser')).toBeInTheDocument();
      // The search filter should be visible in catalog mode
      expect(screen.getByPlaceholderText('Search by name, id, or tag')).toBeInTheDocument();
    });

    it('switches to custom form view when Custom tab is clicked', async () => {
      await renderPage();
      const customTab = screen.getByRole('button', { name: 'Custom' });
      await fireEvent.click(customTab);

      expect(screen.getByText('Add Custom Server')).toBeInTheDocument();
      // The catalog search should be hidden
      expect(screen.queryByPlaceholderText('Search by name, id, or tag')).toBeNull();
    });

    it('switches back to catalog when Catalog tab is clicked', async () => {
      await renderPage();
      // Go to custom
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));
      expect(screen.getByText('Add Custom Server')).toBeInTheDocument();

      // Back to catalog
      await fireEvent.click(screen.getByRole('button', { name: 'Catalog' }));
      expect(screen.getByText('Catalog Browser')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Search by name, id, or tag')).toBeInTheDocument();
    });
  });

  // =========================================================================
  // Custom form rendering
  // =========================================================================
  describe('custom form fields', () => {
    it('renders all required form fields', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      expect(screen.getByText('Server ID *')).toBeInTheDocument();
      expect(screen.getByText('Command *')).toBeInTheDocument();
      expect(screen.getByText('Arguments (one per row)')).toBeInTheDocument();
      expect(screen.getByText('Environment Variables')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('my-custom-server')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('npx, uvx, node, python ...')).toBeInTheDocument();
    });

    it('renders one empty argument row by default', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      const argInput = screen.getByPlaceholderText('e.g. -y');
      expect(argInput).toBeInTheDocument();
      expect((argInput as HTMLInputElement).value).toBe('');
    });

    it('renders one empty env var row by default', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      expect(screen.getByPlaceholderText('KEY')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('value')).toBeInTheDocument();
    });

    it('adds an argument row when the add button is clicked', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      const addBtn = screen.getByTitle('Add argument');
      await fireEvent.click(addBtn);

      const argInputs = screen.getAllByPlaceholderText('e.g. -y');
      expect(argInputs).toHaveLength(2);
    });

    it('adds an env var row when the add button is clicked', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      const addBtn = screen.getByTitle('Add env var');
      await fireEvent.click(addBtn);

      const keyInputs = screen.getAllByPlaceholderText('KEY');
      expect(keyInputs).toHaveLength(2);
    });

    it('removes an argument row when the remove button is clicked', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      // Add a second row first
      await fireEvent.click(screen.getByTitle('Add argument'));
      expect(screen.getAllByPlaceholderText('e.g. -y')).toHaveLength(2);

      // Remove the first one
      const removeBtns = screen.getAllByTitle('Remove argument');
      await fireEvent.click(removeBtns[0]);

      // One row should remain (minimum of 1)
      expect(screen.getAllByPlaceholderText('e.g. -y')).toHaveLength(1);
    });

    it('removes an env var row when the remove button is clicked', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      // Add a second row
      await fireEvent.click(screen.getByTitle('Add env var'));
      expect(screen.getAllByPlaceholderText('KEY')).toHaveLength(2);

      // Remove the first
      const removeBtns = screen.getAllByTitle('Remove env var');
      await fireEvent.click(removeBtns[0]);

      expect(screen.getAllByPlaceholderText('KEY')).toHaveLength(1);
    });
  });

  // =========================================================================
  // Form validation
  // =========================================================================
  describe('form validation', () => {
    it('shows error when server ID is empty', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      // Click Preview without filling anything
      const previewBtn = screen.getByRole('button', { name: 'Preview config' });
      await fireEvent.click(previewBtn);

      expect(screen.getByText('Server ID is required.')).toBeInTheDocument();
      expect(mocks.mockConfigureCustomMcp).not.toHaveBeenCalled();
    });

    it('shows error when server ID has invalid format', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      const serverIdInput = screen.getByPlaceholderText('my-custom-server');
      await fireEvent.input(serverIdInput, { target: { value: 'Invalid Name!' } });

      const cmdInput = screen.getByPlaceholderText('npx, uvx, node, python ...');
      await fireEvent.input(cmdInput, { target: { value: 'npx' } });

      const previewBtn = screen.getByRole('button', { name: 'Preview config' });
      await fireEvent.click(previewBtn);

      expect(screen.getByText('Must be lowercase alphanumeric with hyphens (e.g. my-server).')).toBeInTheDocument();
      expect(mocks.mockConfigureCustomMcp).not.toHaveBeenCalled();
    });

    it('shows error when command is empty', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      const serverIdInput = screen.getByPlaceholderText('my-custom-server');
      await fireEvent.input(serverIdInput, { target: { value: 'my-server' } });

      const previewBtn = screen.getByRole('button', { name: 'Preview config' });
      await fireEvent.click(previewBtn);

      expect(screen.getByText('Command is required.')).toBeInTheDocument();
      expect(mocks.mockConfigureCustomMcp).not.toHaveBeenCalled();
    });

    it('clears validation errors on successful submission', async () => {
      mocks.mockConfigureCustomMcp.mockResolvedValue({
        applied: false,
        config: { mcpServers: { 'my-server': { command: 'npx' } } },
        commands: [],
        path: null,
        warnings: [],
      });

      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      // First trigger a validation error
      await fireEvent.click(screen.getByRole('button', { name: 'Preview config' }));
      expect(screen.getByText('Server ID is required.')).toBeInTheDocument();

      // Now fill in valid data and submit
      await fireEvent.input(screen.getByPlaceholderText('my-custom-server'), { target: { value: 'my-server' } });
      await fireEvent.input(screen.getByPlaceholderText('npx, uvx, node, python ...'), { target: { value: 'npx' } });
      await fireEvent.click(screen.getByRole('button', { name: 'Preview config' }));

      await waitFor(() => {
        expect(screen.queryByText('Server ID is required.')).toBeNull();
      });
    });
  });

  // =========================================================================
  // API wiring
  // =========================================================================
  describe('API integration', () => {
    it('calls configureCustomMcp with apply=false on preview', async () => {
      mocks.mockConfigureCustomMcp.mockResolvedValue({
        applied: false,
        config: { mcpServers: { 'my-server': { command: 'npx', args: ['-y', 'my-pkg'] } } },
        commands: [],
        path: null,
        warnings: [],
      });

      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      await fireEvent.input(screen.getByPlaceholderText('my-custom-server'), { target: { value: 'my-server' } });
      await fireEvent.input(screen.getByPlaceholderText('npx, uvx, node, python ...'), { target: { value: 'npx' } });

      // Fill in the first arg row and add a second
      const argInput = screen.getByPlaceholderText('e.g. -y');
      await fireEvent.input(argInput, { target: { value: '-y' } });
      await fireEvent.click(screen.getByTitle('Add argument'));
      const argInputs = screen.getAllByPlaceholderText('e.g. -y');
      await fireEvent.input(argInputs[1], { target: { value: 'my-pkg' } });

      await fireEvent.click(screen.getByRole('button', { name: 'Preview config' }));

      await waitFor(() => {
        expect(mocks.mockConfigureCustomMcp).toHaveBeenCalledWith(
          expect.objectContaining({
            server_id: 'my-server',
            command: 'npx',
            args: ['-y', 'my-pkg'],
            client: 'cursor',
            apply: false,
          }),
        );
      });
    });

    it('shows preview status message after successful preview', async () => {
      mocks.mockConfigureCustomMcp.mockResolvedValue({
        applied: false,
        config: { mcpServers: { 'my-server': { command: 'npx' } } },
        commands: [],
        path: null,
        warnings: [],
      });

      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      await fireEvent.input(screen.getByPlaceholderText('my-custom-server'), { target: { value: 'my-server' } });
      await fireEvent.input(screen.getByPlaceholderText('npx, uvx, node, python ...'), { target: { value: 'npx' } });
      await fireEvent.click(screen.getByRole('button', { name: 'Preview config' }));

      await waitFor(() => {
        expect(screen.getByText('Custom server preview updated.')).toBeInTheDocument();
      });
    });

    it('sends env vars in the payload', async () => {
      mocks.mockConfigureCustomMcp.mockResolvedValue({
        applied: false,
        config: {},
        commands: [],
        path: null,
        warnings: [],
      });

      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      await fireEvent.input(screen.getByPlaceholderText('my-custom-server'), { target: { value: 'my-server' } });
      await fireEvent.input(screen.getByPlaceholderText('npx, uvx, node, python ...'), { target: { value: 'node' } });
      await fireEvent.input(screen.getByPlaceholderText('KEY'), { target: { value: 'MY_TOKEN' } });
      await fireEvent.input(screen.getByPlaceholderText('value'), { target: { value: 'secret123' } });

      await fireEvent.click(screen.getByRole('button', { name: 'Preview config' }));

      await waitFor(() => {
        expect(mocks.mockConfigureCustomMcp).toHaveBeenCalledWith(
          expect.objectContaining({
            env: { MY_TOKEN: 'secret123' },
          }),
        );
      });
    });

    it('shows error message when API call fails', async () => {
      mocks.mockConfigureCustomMcp.mockRejectedValue(new Error('Network error'));

      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));

      await fireEvent.input(screen.getByPlaceholderText('my-custom-server'), { target: { value: 'my-server' } });
      await fireEvent.input(screen.getByPlaceholderText('npx, uvx, node, python ...'), { target: { value: 'npx' } });
      await fireEvent.click(screen.getByRole('button', { name: 'Preview config' }));

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });
    });
  });

  // =========================================================================
  // Catalog / custom badges in status panel
  // =========================================================================
  describe('catalog/custom status badges', () => {
    it('shows "catalog" badge for a server that matches the catalog', async () => {
      mocks.mockGetMcpStatus.mockResolvedValue({
        client: 'cursor',
        path: '/home/user/.cursor/mcp.json',
        configured: {
          'brave-search': { command: 'npx', args: ['-y', '@anthropic/mcp-brave-search'] },
        },
        settings: {},
        count: 1,
      });

      await renderPage();

      expect(screen.getByText('brave-search')).toBeInTheDocument();
      expect(screen.getByText('catalog')).toBeInTheDocument();
      expect(screen.queryByText('custom')).toBeNull();
    });

    it('shows "custom" badge for a server not in the catalog', async () => {
      mocks.mockGetMcpStatus.mockResolvedValue({
        client: 'cursor',
        path: '/home/user/.cursor/mcp.json',
        configured: {
          'my-private-server': { command: 'node', args: ['server.js'] },
        },
        settings: {},
        count: 1,
      });

      await renderPage();

      expect(screen.getByText('my-private-server')).toBeInTheDocument();
      expect(screen.getByText('custom')).toBeInTheDocument();
      expect(screen.queryByText('catalog')).toBeNull();
    });

    it('shows both badges when catalog and custom servers are configured', async () => {
      mocks.mockGetMcpStatus.mockResolvedValue({
        client: 'cursor',
        path: '/home/user/.cursor/mcp.json',
        configured: {
          'brave-search': { command: 'npx', args: [] },
          'my-private-server': { command: 'node', args: [] },
        },
        settings: {},
        count: 2,
      });

      await renderPage();

      expect(screen.getByText('brave-search')).toBeInTheDocument();
      expect(screen.getByText('my-private-server')).toBeInTheDocument();
      expect(screen.getByText('catalog')).toBeInTheDocument();
      expect(screen.getByText('custom')).toBeInTheDocument();
    });
  });

  // =========================================================================
  // Preview panel context awareness
  // =========================================================================
  describe('preview panel', () => {
    it('shows catalog-specific placeholder in catalog mode', async () => {
      await renderPage();
      expect(screen.getByText('Select one or more servers, then click "Preview config".')).toBeInTheDocument();
    });

    it('shows custom-specific placeholder in custom mode', async () => {
      await renderPage();
      await fireEvent.click(screen.getByRole('button', { name: 'Custom' }));
      expect(screen.getByText('Fill in the custom server form, then click "Preview config".')).toBeInTheDocument();
    });
  });
});
