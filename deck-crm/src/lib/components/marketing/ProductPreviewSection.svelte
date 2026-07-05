<script lang="ts">
  import { previewPanes } from '$lib/data/marketing/home';
</script>

<section class="panel section">
  <div class="section-head">
    <div>
      <div class="eyebrow">Product preview</div>
      <h2>Preview the operating surface before sign-in.</h2>
    </div>
    <p class="muted">
      The public site previews the shape of the workflow, while the app keeps the real deck, findings, and
      edits inside the signed-in shell.
    </p>
  </div>

  <div class="preview-grid">
    {#each previewPanes as pane}
      <article>
        <strong>{pane.title}</strong>
        <p class="muted">{pane.body}</p>
      </article>
    {/each}
  </div>
</section>

<style>
  .section {
    padding: 1.45rem;
    display: grid;
    gap: 1rem;
  }

  .section-head {
    display: grid;
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    gap: 1rem;
    align-items: end;
  }

  .section-head h2 {
    margin: 0.35rem 0 0;
  }

  .preview-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .preview-grid article {
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1.1rem;
    background: var(--surface-soft);
  }

  @media (max-width: 960px) {
    .section-head,
    .preview-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
