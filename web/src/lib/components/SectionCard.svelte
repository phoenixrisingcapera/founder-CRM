<script lang="ts">
  export let title = '';
  export let subtitle = '';
</script>

<section class="panel">
  {#if title}
    <div style="display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; margin-bottom:1rem;">
      <div>
        <h2 style="margin:0 0 0.35rem 0; font-size:1.1rem;">{title}</h2>
        {#if subtitle}
          <p class="muted" style="margin:0;">{subtitle}</p>
        {/if}
      </div>
      <slot name="actions" />
    </div>
  {/if}
  <slot />
</section>
