<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { ensureSession } from '$lib/api';

  onMount(async () => {
    try {
      await ensureSession();
      goto('/dashboard');
    } catch {
      goto('/auth');
    }
  });
</script>

<div class="panel">Loading workspace...</div>
