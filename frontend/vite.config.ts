import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { svelteTesting } from '@testing-library/svelte/vite';
import path from 'path';
import fs from 'fs';

function getProjectVersion(): string {
  const toml = fs.readFileSync(path.resolve(__dirname, '../pyproject.toml'), 'utf-8');
  const match = toml.match(/^version\s*=\s*"(.+?)"/m);
  return match ? match[1] : '0.0.0';
}

export default defineConfig({
  define: {
    __APP_VERSION__: JSON.stringify(getProjectVersion()),
  },
  plugins: [
    svelte({ compilerOptions: { hmr: !process.env.VITEST } }),
    svelteTesting(),
  ],
  build: {
    outDir: '../api/static/dist',
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      $lib: path.resolve('./src/lib'),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler',
        loadPaths: [
          path.resolve('./src'),
          path.resolve('./src/lib'),
          path.resolve('./src/lib/components'),
        ],
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.test.ts'],
    setupFiles: ['src/test-setup.ts'],
  },
});
