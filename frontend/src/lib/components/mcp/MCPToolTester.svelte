<script lang="ts">
  import { onMount } from 'svelte';
  import { getMcpTools, testMcpTool } from '$lib/api/client';
  import type { McpToolInfo } from '$lib/api/types';
  import Button from '../shared/Button.svelte';
  import LoadingSpinner from '../shared/LoadingSpinner.svelte';
  import { Play, RotateCcw, Save, Trash2, Wrench } from 'lucide-svelte';

  type SavedPreset = {
    id: string;
    name: string;
    toolName: string;
    payload: string;
    savedAt: string;
  };

  const STORAGE_KEY = 'stratifyai.mcp-tool-presets';

  let tools: McpToolInfo[] = [];
  let selectedToolName = '';
  let requestBody = '{}';
  let responseBody = '';
  let presetName = '';
  let presets: SavedPreset[] = [];
  let loading = true;
  let executing = false;
  let error: string | null = null;
  let statusMessage = '';

  onMount(() => {
    loadPresets();
    void loadTools();
  });

  async function loadTools() {
    try {
      loading = true;
      error = null;
      const response = await getMcpTools();
      tools = response.tools;

      if (tools.length > 0) {
        selectedToolName = selectedToolName || tools[0].name;
        resetToExample();
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load MCP tools';
    } finally {
      loading = false;
    }
  }

  function loadPresets() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      presets = raw ? (JSON.parse(raw) as SavedPreset[]) : [];
    } catch {
      presets = [];
    }
  }

  function persistPresets() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(presets));
  }

  function resetToExample() {
    const tool = tools.find((item) => item.name === selectedToolName);
    requestBody = JSON.stringify(tool?.example_payload ?? {}, null, 2);
    statusMessage = '';
    error = null;
  }

  async function runTool() {
    try {
      executing = true;
      error = null;
      statusMessage = '';
      const payload = requestBody.trim() ? JSON.parse(requestBody) : {};
      const response = await testMcpTool({
        tool_name: selectedToolName,
        payload,
      });
      responseBody = JSON.stringify(response.result, null, 2);
      statusMessage = `Executed ${selectedToolName} successfully.`;
    } catch (err) {
      responseBody = '';
      error = err instanceof Error ? err.message : 'Tool execution failed';
    } finally {
      executing = false;
    }
  }

  function savePreset() {
    const name = presetName.trim() || `${selectedToolName} preset`;
    const preset: SavedPreset = {
      id: `${Date.now()}`,
      name,
      toolName: selectedToolName,
      payload: requestBody,
      savedAt: new Date().toISOString(),
    };

    presets = [preset, ...presets.filter((item) => item.name !== name)];
    persistPresets();
    presetName = '';
    statusMessage = `Saved preset “${name}”.`;
  }

  function applyPreset(preset: SavedPreset) {
    selectedToolName = preset.toolName;
    requestBody = preset.payload;
    statusMessage = `Loaded preset “${preset.name}”.`;
    error = null;
  }

  function deletePreset(presetId: string) {
    presets = presets.filter((item) => item.id !== presetId);
    persistPresets();
    statusMessage = 'Preset removed.';
  }

  $: selectedTool = tools.find((item) => item.name === selectedToolName) ?? null;
  $: schemaText = JSON.stringify(selectedTool?.input_schema ?? {}, null, 2);
</script>

<section class="tool-tester card">
  <div class="section-title">
    <Wrench size={18} />
    <div>
      <h2>Inline Tool Tester</h2>
      <p>Browse the available MCP tools, edit JSON input, run a tool, and save reusable presets.</p>
    </div>
  </div>

  {#if loading}
    <div class="loading-state">
      <LoadingSpinner size="lg" />
      <span>Loading tool metadata...</span>
    </div>
  {:else}
    <div class="tester-grid">
      <div class="browser-panel">
        <label>
          <span>Tool</span>
          <select bind:value={selectedToolName} on:change={resetToExample}>
            {#each tools as tool}
              <option value={tool.name}>{tool.name} — {tool.category}</option>
            {/each}
          </select>
        </label>

        {#if selectedTool}
          <div class="tool-meta">
            <h3>{selectedTool.name}</h3>
            <p>{selectedTool.description}</p>
            <span class="chip">{selectedTool.category}</span>
          </div>

          <div class="schema-block">
            <div class="block-header">
              <strong>Schema</strong>
              <Button variant="ghost" size="sm" on:click={resetToExample}>
                <RotateCcw size={14} />
                Reset example
              </Button>
            </div>
            <pre>{schemaText}</pre>
          </div>
        {/if}

        <div class="preset-block">
          <div class="block-header">
            <strong>Saved Presets</strong>
          </div>

          <div class="preset-save-row">
            <input type="text" bind:value={presetName} placeholder="Preset name" />
            <Button variant="secondary" size="sm" on:click={savePreset}>
              <Save size={14} />
              Save
            </Button>
          </div>

          {#if presets.length === 0}
            <p class="muted">No saved presets yet.</p>
          {:else}
            <div class="preset-list">
              {#each presets as preset (preset.id)}
                <div class="preset-item">
                  <button class="preset-load" on:click={() => applyPreset(preset)}>
                    <strong>{preset.name}</strong>
                    <span>{preset.toolName}</span>
                  </button>
                  <button class="preset-delete" on:click={() => deletePreset(preset.id)} aria-label={`Delete ${preset.name}`}>
                    <Trash2 size={14} />
                  </button>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>

      <div class="editor-panel">
        <label>
          <span>JSON request payload</span>
          <textarea bind:value={requestBody} rows="14" spellcheck="false"></textarea>
        </label>

        <div class="action-row">
          <Button variant="primary" on:click={runTool} loading={executing}>
            <Play size={14} />
            Execute tool
          </Button>
        </div>

        {#if statusMessage}
          <p class="success-text">{statusMessage}</p>
        {/if}
        {#if error}
          <p class="error-text">{error}</p>
        {/if}

        <div class="response-block">
          <strong>Response</strong>
          <pre>{responseBody || 'Run a tool to view the response here.'}</pre>
        </div>
      </div>
    </div>
  {/if}
</section>

<style lang="scss">
  @use '../../../styles/tokens' as *;
  @use '../../../styles/mixins' as *;

  .card {
    background: var(--bg-surface);
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-xl;
    padding: $space-4;
    box-shadow: $shadow-sm;
  }

  .section-title {
    display: flex;
    gap: $space-3;
    align-items: flex-start;
    margin-bottom: $space-4;

    h2 {
      margin: 0 0 $space-1;
      color: var(--text-primary);
      font-size: $text-lg;
    }

    p {
      margin: 0;
      color: var(--text-secondary);
      font-size: $text-sm;
    }
  }

  .tester-grid {
    display: grid;
    grid-template-columns: minmax(280px, 0.95fr) minmax(0, 1.25fr);
    gap: $space-4;

    @media (max-width: 1100px) {
      grid-template-columns: 1fr;
    }
  }

  .browser-panel,
  .editor-panel,
  .schema-block,
  .preset-block,
  .response-block {
    display: flex;
    flex-direction: column;
    gap: $space-3;
  }

  .tool-meta {
    p {
      margin: 0;
      color: var(--text-secondary);
      font-size: $text-sm;
    }

    h3 {
      margin: 0 0 $space-1;
      color: var(--text-primary);
      font-size: $text-base;
    }
  }

  .chip {
    display: inline-flex;
    width: fit-content;
    border-radius: 999px;
    background: var(--bg-elevated);
    color: var(--text-secondary);
    padding: $space-1 $space-2;
    font-size: $text-xs;
    font-weight: $font-medium;
  }

  .block-header,
  .action-row,
  .preset-save-row,
  .preset-item {
    display: flex;
    gap: $space-2;
    align-items: center;
    justify-content: space-between;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: $space-1;

    span {
      color: var(--text-secondary);
      font-size: $text-sm;
    }
  }

  select,
  input,
  textarea {
    width: 100%;
    border: 1px solid var(--bg-hover);
    background: var(--bg-base);
    color: var(--text-primary);
    border-radius: $radius-lg;
    padding: $space-2 $space-3;
    font-size: $text-sm;
    font-family: $font-sans;
  }

  textarea,
  pre {
    font-family: $font-mono;
  }

  pre {
    margin: 0;
    min-height: 120px;
    padding: $space-3;
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-lg;
    background: var(--bg-base);
    color: var(--text-primary);
    font-size: $text-xs;
    white-space: pre-wrap;
    overflow: auto;
  }

  .preset-list {
    display: flex;
    flex-direction: column;
    gap: $space-2;
  }

  .preset-item {
    border: 1px solid var(--bg-elevated);
    border-radius: $radius-lg;
    padding: $space-2;
    background: var(--bg-base);
  }

  .preset-load,
  .preset-delete {
    border: none;
    background: transparent;
    color: var(--text-primary);
    cursor: pointer;
  }

  .preset-load {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;

    span {
      font-size: $text-xs;
      color: var(--text-secondary);
    }
  }

  .muted {
    margin: 0;
    color: var(--text-secondary);
    font-size: $text-sm;
  }

  .success-text {
    margin: 0;
    color: #10b981;
    font-size: $text-sm;
  }

  .error-text {
    margin: 0;
    color: #ef4444;
    font-size: $text-sm;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: $space-3;
    min-height: 180px;
    color: var(--text-secondary);
  }
</style>
