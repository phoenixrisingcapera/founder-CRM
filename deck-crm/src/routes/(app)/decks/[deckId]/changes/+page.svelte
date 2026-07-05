<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
</script>

<AppShell title="Change review" subtitle="Change review now lives on Due Diligence." activeNav="diligence">
  <section class="panel changes-redirect">
    <div class="eyebrow">Moved</div>
    <h2>Change review is part of Due Diligence</h2>
    <p class="muted">This route redirects to the persistent Due Diligence workspace.</p>
  </section>
</AppShell>

<style>
  .changes-redirect {
    padding: 1.25rem;
  }

  h2,
  p {
    margin: 0;
  }
</style>
