<script lang="ts">
  import type { RenderSchema } from '$lib/api/smartDeckWorkspace';

  interface Props {
    renderSchema?: RenderSchema | null;
    designTokens?: Record<string, string> | null;
    selectedElementId?: string | null;
    onSelectElement?: (elementId: string) => void;
  }

  let { renderSchema = null, designTokens = null, selectedElementId = null, onSelectElement }: Props = $props();

  const tokens = $derived<Record<string, string>>({
    'brand.surface': 'var(--surface-strong)',
    'brand.surfaceAlt': 'var(--surface)',
    'brand.heading': 'var(--ink-strong)',
    'brand.body': 'var(--ink)',
    'brand.accent': 'var(--accent)',
    'brand.muted': 'var(--muted)',
    ...(designTokens ?? {})
  });

  function tokenValue(value?: string | null) {
    if (!value) return 'var(--ink)';
    return tokens[value] ?? value;
  }

  function assetUrl(value?: string | null) {
    if (!value) return '';
    if (value.startsWith('/api/') || value.startsWith('/uploads/') || value.startsWith('/static/')) return value;
    return '';
  }

  function backgroundStyle(schema: RenderSchema) {
    const background = schema.background;
    if (background.type === 'layered') return tokenValue(background.fill);
    if (background.type === 'token') return tokenValue(background.value);
    if (background.type === 'gradient') {
      return (background.value ?? '')
        .replaceAll('brand.surfaceAlt', tokenValue('brand.surfaceAlt'))
        .replaceAll('brand.surface', tokenValue('brand.surface'))
        .replaceAll('brand.accent', tokenValue('brand.accent'));
    }
    if (background.type === 'image') return `center / cover no-repeat url("${assetUrl(background.value)}")`;
    return background.value ?? 'var(--surface-input-strong)';
  }

  function backgroundLayerStyle(layer: NonNullable<RenderSchema['background']['layers']>[number], schema: RenderSchema) {
    const left = (layer.x / schema.width) * 100;
    const top = (layer.y / schema.height) * 100;
    const width = (layer.width / schema.width) * 100;
    const height = (layer.height / schema.height) * 100;
    const fill = tokenValue(layer.style?.fill);
    const opacity = layer.style?.opacity ?? 1;
    const radius = layer.shape === 'circle' ? 999 : layer.style?.radius ?? 0;
    return [
      `left:${left}%`,
      `top:${top}%`,
      `width:${width}%`,
      `height:${height}%`,
      `z-index:${layer.zIndex ?? 0}`,
      `background:${layer.type === 'shape' ? fill : 'transparent'}`,
      `opacity:${opacity}`,
      `border-radius:${radius}px`
    ].join(';');
  }

  function elementStyle(element: RenderSchema['elements'][number], schema: RenderSchema) {
    const left = (element.x / schema.width) * 100;
    const top = (element.y / schema.height) * 100;
    const width = (element.width / schema.width) * 100;
    const height = (element.height / schema.height) * 100;
    const fontSize = element.fontSize ? `${(element.fontSize / schema.height) * 100}%` : '3%';
    const color = tokenValue(element.colorToken);
    const fill = tokenValue(element.fillToken);
    return [
      `left:${left}%`,
      `top:${top}%`,
      `width:${width}%`,
      `height:${height}%`,
      `z-index:${element.zIndex ?? 20}`,
      `font-size:${fontSize}`,
      `color:${color}`,
      `background:${element.type === 'shape' ? fill : 'transparent'}`
    ].join(';');
  }
</script>

{#if renderSchema}
  <div class="render-stage" style={`background:${backgroundStyle(renderSchema)}`}>
    {#if renderSchema.background.type === 'layered'}
      {#each renderSchema.background.layers ?? [] as layer}
        {#if layer.type === 'image' && assetUrl(layer.assetUrl)}
          <img class="background-layer" style={backgroundLayerStyle(layer, renderSchema)} src={assetUrl(layer.assetUrl)} alt="" />
        {:else if layer.type === 'shape'}
          <div class="background-layer" style={backgroundLayerStyle(layer, renderSchema)}></div>
        {/if}
      {/each}
    {/if}
    {#each renderSchema.elements as element}
      {#if element.type === 'image' && element.assetUrl}
        <button
          class="render-element image"
          class:selected={selectedElementId === element.id}
          style={elementStyle(element, renderSchema)}
          type="button"
          aria-label={`Select generated image element ${element.id}`}
          onclick={() => onSelectElement?.(element.id)}
        >
          <img src={assetUrl(element.assetUrl)} alt="" />
        </button>
      {:else if element.type === 'shape'}
        <button
          class="render-element shape"
          class:selected={selectedElementId === element.id}
          style={elementStyle(element, renderSchema)}
          type="button"
          aria-label={`Select generated shape element ${element.id}`}
          onclick={() => onSelectElement?.(element.id)}
        ></button>
      {:else}
        <button
          class="render-element text"
          class:selected={selectedElementId === element.id}
          style={elementStyle(element, renderSchema)}
          type="button"
          aria-label={`Select generated text element ${element.id}`}
          onclick={() => onSelectElement?.(element.id)}
        >
          <span style={`font-weight:${element.fontWeight ?? 400}`}>{element.text}</span>
        </button>
      {/if}
    {/each}
  </div>
{:else}
  <div class="render-empty">No render schema saved</div>
{/if}

<style>
  .render-stage,
  .render-empty {
    width: min(100%, 72rem);
    aspect-ratio: 16 / 9;
    border-radius: 8px;
    border: 1px solid color-mix(in srgb, var(--line-strong) 72%, transparent);
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow);
  }

  .render-empty {
    display: grid;
    place-items: center;
    color: var(--muted);
  }

  .render-element {
    position: absolute;
    overflow: hidden;
    border: 1px solid transparent;
    padding: 0;
    text-align: left;
    font: inherit;
    cursor: pointer;
    appearance: none;
    z-index: 20;
  }

  .background-layer {
    position: absolute;
    display: block;
    pointer-events: none;
  }

  .render-element.text {
    display: flex;
    align-items: flex-start;
    line-height: 1.08;
    overflow-wrap: anywhere;
  }

  .render-element.text span {
    display: block;
  }

  .render-element.shape {
    border-radius: 999px;
  }

  .render-element.image {
    display: block;
  }

  .render-element.image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  .render-element:hover,
  .render-element.selected {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px var(--accent-soft);
  }
</style>
