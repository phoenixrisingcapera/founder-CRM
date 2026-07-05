let adapterModule;

try {
  adapterModule = await import('@sveltejs/adapter-node');
} catch {
  adapterModule = await import('@sveltejs/adapter-auto');
}

const adapter = adapterModule.default;

/** @type {import('@sveltejs/kit').Config} */
const config = {
  kit: {
    adapter: adapter()
  }
};

export default config;
