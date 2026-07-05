<script lang="ts">
  export let title: string;
  export let body = '';
</script>

<div style="padding:1.1rem; border:1px dashed var(--color-border); border-radius:14px; background:#fffdf9;">
  <h3 style="margin:0 0 0.35rem 0;">{title}</h3>
  <p class="muted" style="margin:0;">{body}</p>
</div>
