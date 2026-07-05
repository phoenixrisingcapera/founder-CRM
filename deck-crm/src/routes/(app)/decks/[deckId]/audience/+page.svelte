<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
</script>

<AppShell title="Audience" subtitle="Audience recommendations live on Due Diligence." activeNav="diligence">
  <section class="panel audience-redirect">
    <div class="eyebrow">Moved</div>
    <h2>Audience recommendations are part of Due Diligence</h2>
    <p class="muted">This route redirects to the persistent Due Diligence workspace.</p>
  </section>
</AppShell>

<style>
  .audience-redirect {
    padding: 1.25rem;
  }

  h2,
  p {
    margin: 0;
  }
</style>
