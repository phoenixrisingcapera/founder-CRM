<script lang="ts">
  import { vcUseCases } from '$lib/data/marketing/home';
</script>

<section class="panel section">
  <div class="grid">
    <div class="copy">
      <div class="eyebrow">For VCs</div>
      <h2>Built for funds that need a better review system than PDFs, chat threads, and last-minute rewrites.</h2>
      <p class="muted">
        From first-look screening to partner discussion and IC prep, Deck AIStack keeps the source narrative,
        review state, and AI output inside one operating surface the team can actually trust.
      </p>
      <a class="button secondary" href="/vcs">Learn more for VCs</a>
    </div>

    <div class="use-cases">
      {#each vcUseCases as useCase}
        <article>
          <strong>{useCase.title}</strong>
          <p class="muted">{useCase.body}</p>
        </article>
      {/each}
    </div>
  </div>
</section>

<style>
  .section {
    padding: 1.45rem;
  }

  .grid {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) 420px;
    gap: 1rem;
    align-items: start;
  }

  .copy {
    display: grid;
    gap: 0.85rem;
    align-content: start;
  }

  .use-cases {
    display: grid;
    gap: 0.9rem;
  }

  .use-cases article {
    border: 1px solid var(--line);
    border-radius: 18px;
    padding: 1rem;
    background: var(--surface-soft);
  }

  .use-cases p {
    margin: 0.45rem 0 0;
  }

  @media (max-width: 960px) {
    .grid {
      grid-template-columns: 1fr;
    }
  }
</style>
