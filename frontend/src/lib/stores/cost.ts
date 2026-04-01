// ============================================
// COST STORE - Session cost tracking
// ============================================

import { writable, derived, get } from 'svelte/store';

interface CostEntry {
  provider: string;
  model: string;
  cost: number;
  tokens: number;
  timestamp: Date;
}

function createCostStore() {
  const entries = writable<CostEntry[]>([]);
  
  const totalCost = derived(entries, $entries => 
    $entries.reduce((sum, e) => sum + e.cost, 0)
  );
  
  const totalTokens = derived(entries, $entries => 
    $entries.reduce((sum, e) => sum + e.tokens, 0)
  );
  
  const totalCalls = derived(entries, $entries => $entries.length);
  
  const byProvider = derived(entries, $entries => {
    const result: Record<string, { cost: number; tokens: number; calls: number }> = {};
    for (const entry of $entries) {
      if (!result[entry.provider]) {
        result[entry.provider] = { cost: 0, tokens: 0, calls: 0 };
      }
      result[entry.provider].cost += entry.cost;
      result[entry.provider].tokens += entry.tokens;
      result[entry.provider].calls += 1;
    }
    return result;
  });
  
  // Combined store for reactive $costStore access
  const store = derived(
    [entries, totalCost, totalTokens, totalCalls, byProvider],
    ([$entries, $totalCost, $totalTokens, $totalCalls, $byProvider]) => ({
      entries: $entries,
      totalCost: $totalCost,
      totalTokens: $totalTokens,
      totalCalls: $totalCalls,
      byProvider: $byProvider,
    })
  );
  
  return {
    store,
    actions: {
      addEntry(provider: string, model: string, cost: number, tokens: number) {
        entries.update(e => [...e, {
          provider,
          model,
          cost,
          tokens,
          timestamp: new Date(),
        }]);
      },
      
      clear() {
        entries.set([]);
      },
    },
  };
}

const { store, actions } = createCostStore();
export const costStore = store;
export const costActions = actions;
