import { resolve } from 'node:path';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  // NOTE:
  // In Docker bind-mount dev setups (macOS especially), TanStack's route-tree
  // generator can end up in a rewrite race on `routeTree.gen.ts`, which keeps
  // Vite from binding to the dev port. We keep the checked-in generated file
  // and disable plugin-time regeneration for stable local dev.
  plugins: [react()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
});
