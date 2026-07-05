<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
</script>

<AppShell title="Slides" subtitle="Admin access required." activeNav="admin">
  <section class="panel restricted-slides">
    <div class="eyebrow">Restricted</div>
    <h2>Admin access required</h2>
    <p class="muted">The parsed slide inspector is available from the admin area.</p>
    <a class="button secondary" href="/dashboard">Back to dashboard</a>
  </section>
</AppShell>

<style>
  .restricted-slides {
    padding: 1.25rem;
  }

  h2,
  p {
    margin: 0;
  }
</style>
