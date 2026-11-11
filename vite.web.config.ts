import {defineConfig} from 'vite';
import {svelte} from '@sveltejs/vite-plugin-svelte';
import {resolve} from 'node:path';
import {lazyDependencies} from './vite.config';

export default defineConfig({
  plugins: [svelte()],
  optimizeDeps: {entries: ['web/index.html', 'tests/bs/index.html'], include: lazyDependencies},
  build: {
    target: 'es2022',
    outDir: 'dist-web',
    rollupOptions: {input: resolve('web/index.html')},
  },
  server: {host: '127.0.0.1', port: 1428, strictPort: true},
});
