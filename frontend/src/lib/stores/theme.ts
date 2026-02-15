// ============================================
// THEME STORE - Dark/Light mode with persistence
// ============================================

import { writable, derived, get } from 'svelte/store';

type Theme = 'dark' | 'light' | 'system';

function getSystemTheme(): 'dark' | 'light' {
  if (typeof window === 'undefined') return 'dark';
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

function createThemeStore() {
  const theme = writable<Theme>('system');
  const resolved = writable<'dark' | 'light'>('dark');
  
  const isDark = derived(resolved, $resolved => $resolved === 'dark');
  
  function applyTheme(t: Theme) {
    if (typeof document === 'undefined') return;
    
    const html = document.documentElement;
    
    if (t === 'system') {
      html.removeAttribute('data-theme');
      resolved.set(getSystemTheme());
    } else {
      html.setAttribute('data-theme', t);
      resolved.set(t);
    }
  }
  
  // Derived store that combines resolved and isDark for reactive access
  const store = derived(
    [theme, resolved, isDark],
    ([$theme, $resolved, $isDark]) => ({
      theme: $theme,
      resolved: $resolved,
      isDark: $isDark,
    })
  );
  
  return {
    store,
    actions: {
      init() {
        if (typeof window === 'undefined') return;
        
        // Load saved preference
        const saved = localStorage.getItem('stratifyai-theme') as Theme | null;
        if (saved && ['dark', 'light', 'system'].includes(saved)) {
          theme.set(saved);
        }
        
        applyTheme(get(theme));
        
        // Listen for system preference changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
        mediaQuery.addEventListener('change', () => {
          if (get(theme) === 'system') {
            resolved.set(getSystemTheme());
          }
        });
      },
      
      setTheme(t: Theme) {
        theme.set(t);
        applyTheme(t);
        localStorage.setItem('stratifyai-theme', t);
      },
      
      toggle() {
        const r = get(resolved);
        const next = r === 'dark' ? 'light' : 'dark';
        this.setTheme(next);
      },
    },
  };
}

const { store, actions } = createThemeStore();
export const themeStore = store;
export const themeActions = actions;
