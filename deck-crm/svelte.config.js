import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter(),
    alias: {
      '@deck-aistack-codes/shared': 'src/lib/contracts/index.ts',
      $components: 'src/lib/components',
      $server: 'src/lib/server',
      $types: 'src/lib/types'
    }
  }
};

export default config;
