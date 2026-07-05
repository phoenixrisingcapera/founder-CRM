<script lang="ts">
  interface Props {
    enabled?: boolean;
    children?: import('svelte').Snippet;
  }

  let { enabled = false, children }: Props = $props();
</script>

{#if enabled}
  <div class="mobile-blocker">
    <section class="panel mobile-blocker__card">
      <div class="eyebrow">Desktop workspace</div>
      <h1>Deck editing requires laptop or desktop.</h1>
      <p class="muted">
        This workspace is designed for laptop/desktop. You can still view decks and download exports from the mobile dashboard.
      </p>
    </section>
  </div>
{:else}
  {@render children?.()}
{/if}
