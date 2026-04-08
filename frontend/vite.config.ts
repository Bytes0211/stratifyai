import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { svelteTesting } from '@testing-library/svelte/vite';
import path from 'path';

export default defineConfig({
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
