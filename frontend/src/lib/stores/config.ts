// ============================================
// CONFIG STORE - Model configuration state
// ============================================

import { writable, derived } from 'svelte/store';
import type { Provider, ModelInfo } from '$lib/api/types';

const ACTIVE_MCP_SERVERS_STORAGE_KEY = 'stratifyai-active-mcp-servers';

function loadStoredActiveMcpServers(): string[] | null {
  if (typeof window === 'undefined') return null;

  const raw = window.localStorage.getItem(ACTIVE_MCP_SERVERS_STORAGE_KEY);
  if (raw === null) return null;

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter((value): value is string => typeof value === 'string');
  } catch {
    return [];
  }
}

function persistActiveMcpServers(serverIds: string[]) {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(
    ACTIVE_MCP_SERVERS_STORAGE_KEY,
    JSON.stringify(Array.from(new Set(serverIds)))
  );
}

export function hasStoredActiveMcpServersPreference(): boolean {
  if (typeof window === 'undefined') return false;
  return window.localStorage.getItem(ACTIVE_MCP_SERVERS_STORAGE_KEY) !== null;
}

function createConfigStore() {
  const provider = writable<Provider>('anthropic');
  const model = writable<string>('claude-sonnet-4-20250514');
  const temperature = writable<number>(0.7);
  const maxTokens = writable<number | null>(null);
  const chunked = writable<boolean>(false);
  const chunkSize = writable<number>(50000);
  const stream = writable<boolean>(true);
  const activeMcpServers = writable<string[]>(loadStoredActiveMcpServers() ?? []);
  const modelInfo = writable<ModelInfo | null>(null);
  const isReasoningModel = writable<boolean>(false);
  const supportsVision = writable<boolean>(false);
  
  const effectiveTemperature = derived(
    [isReasoningModel, temperature],
    ([$isReasoning, $temp]) => $isReasoning ? 1.0 : $temp
  );
  
  // Combined store for reactive $configStore access
  const store = derived(
    [provider, model, temperature, maxTokens, chunked, chunkSize, stream, activeMcpServers, modelInfo, isReasoningModel, supportsVision, effectiveTemperature],
    ([$provider, $model, $temperature, $maxTokens, $chunked, $chunkSize, $stream, $activeMcpServers, $modelInfo, $isReasoningModel, $supportsVision, $effectiveTemperature]) => ({
      provider: $provider,
      model: $model,
      temperature: $temperature,
      maxTokens: $maxTokens,
      chunked: $chunked,
      chunkSize: $chunkSize,
      stream: $stream,
      activeMcpServers: $activeMcpServers,
      modelInfo: $modelInfo,
      isReasoningModel: $isReasoningModel,
      supportsVision: $supportsVision,
      effectiveTemperature: $effectiveTemperature,
    })
  );
  
  return {
    store,
    actions: {
      setProvider(p: Provider) {
        provider.set(p);
        model.set('');
        modelInfo.set(null);
        isReasoningModel.set(false);
        supportsVision.set(false);
      },
      
      setModel(m: string, info?: ModelInfo) {
        model.set(m);
        if (info) {
          modelInfo.set(info);
          isReasoningModel.set(info.reasoning_model);
          supportsVision.set(info.supports_vision);
        }
      },
      
      setTemperature(t: number) {
        temperature.set(Math.max(0, Math.min(2, t)));
      },
      
      setMaxTokens(t: number | null) {
        maxTokens.set(t);
      },
      
      setChunked(c: boolean) {
        chunked.set(c);
      },
      
      setChunkSize(s: number) {
        chunkSize.set(Math.max(10000, Math.min(100000, s)));
      },
      
      setStream(s: boolean) {
        stream.set(s);
      },

      setActiveMcpServers(serverIds: string[]) {
        const uniqueIds = Array.from(new Set(serverIds));
        activeMcpServers.set(uniqueIds);
        persistActiveMcpServers(uniqueIds);
      },

      toggleActiveMcpServer(serverId: string) {
        activeMcpServers.update((current) => {
          const next = current.includes(serverId)
            ? current.filter((id) => id !== serverId)
            : [...current, serverId];
          persistActiveMcpServers(next);
          return next;
        });
      },
    },
  };
}

const { store, actions } = createConfigStore();
export const configStore = store;
export const configActions = actions;
