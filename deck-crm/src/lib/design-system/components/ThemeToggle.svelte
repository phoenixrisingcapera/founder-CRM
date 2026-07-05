<script lang="ts">
  import { theme } from '$lib/stores/theme';
</script>

<button type="button" class="theme-toggle" aria-label="Toggle theme" onclick={() => theme.toggle()}>
  <span class="theme-toggle__dot"></span>
  <span>{$theme === 'light' ? 'Light' : 'Dark'}</span>
</button>
