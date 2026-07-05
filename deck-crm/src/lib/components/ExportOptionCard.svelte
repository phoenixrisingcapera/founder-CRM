<script lang="ts">
  interface Props {
    title: string;
    detail: string;
    state?: 'idle' | 'selected' | 'ready';
  }

  let { title, detail, state = 'idle' }: Props = $props();
</script>

<article class={`export-card ${state}`}>
  <div class="eyebrow">Output</div>
  <h3>{title}</h3>
  <p>{detail}</p>
  <button class="button {state === 'selected' ? 'secondary' : ''}" type="button">
    {state === 'ready' ? 'Generated' : state === 'selected' ? 'Selected' : 'Select'}
  </button>
</article>

<style>
  .export-card {
    border-radius: 20px;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.03);
    padding: 1rem;
    display: grid;
    gap: 0.65rem;
  }

  .export-card.selected {
    border-color: rgba(104, 161, 255, 0.3);
    background: rgba(104, 161, 255, 0.08);
  }

  .export-card.ready {
    border-color: rgba(84, 179, 126, 0.25);
  }

  h3,
  p {
    margin: 0;
  }

  p {
    color: var(--muted);
  }
</style>
