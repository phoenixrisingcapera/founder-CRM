<script lang="ts">
  interface Props {
    href?: string;
    type?: 'button' | 'submit' | 'reset';
    variant?: 'primary' | 'secondary';
    children?: import('svelte').Snippet;
  }

  let { href, type = 'button', variant = 'primary', children }: Props = $props();
</script>

{#if href}
  <a href={href} class:secondary={variant === 'secondary'} class="button">
    {@render children?.()}
  </a>
{:else}
  <button {type} class:secondary={variant === 'secondary'} class="button">
    {@render children?.()}
  </button>
{/if}
