<script lang="ts">
  interface Props {
    className?: string;
    children?: import('svelte').Snippet;
  }

  let { className = '', children }: Props = $props();
</script>

<section class={`panel ${className}`.trim()}>
  {@render children?.()}
</section>
