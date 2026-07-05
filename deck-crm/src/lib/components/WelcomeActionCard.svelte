<script lang="ts">
  interface Props {
    title: string;
    message: string;
    href?: string | null;
    ctaLabel: string;
    icon?: string;
    meta?: string | null;
    onAction?: (() => void) | null;
  }

  let { title, message, href = null, ctaLabel, icon = '◫', meta = null, onAction = null }: Props = $props();
</script>

<article class="welcome-action-card panel">
  <div class="welcome-action-card__icon" aria-hidden="true">{icon}</div>
  <div class="welcome-action-card__copy">
    <h3>{title}</h3>
    <p>{message}</p>
  </div>

  {#if meta}
    <div class="welcome-action-card__meta">{meta}</div>
  {/if}

  {#if onAction}
    <button class="welcome-action-card__cta" type="button" onclick={onAction}>
      {ctaLabel} <span aria-hidden="true">→</span>
    </button>
  {:else if href}
    <a class="welcome-action-card__cta" href={href}>{ctaLabel} <span aria-hidden="true">→</span></a>
  {/if}
</article>

<style>
  .welcome-action-card {
    min-height: 100%;
    padding: 1.35rem;
    display: grid;
    gap: 1rem;
    background:
      linear-gradient(180deg, rgba(19, 31, 67, 0.92), rgba(10, 17, 38, 0.98)),
      var(--surface-soft);
    border-color: color-mix(in srgb, var(--line-strong) 68%, transparent);
    box-shadow: 0 20px 60px rgba(3, 9, 28, 0.28);
  }

  .welcome-action-card__icon {
    width: 3rem;
    height: 3rem;
    display: grid;
    place-items: center;
    border-radius: 16px;
    font-size: 1.35rem;
    color: var(--accent);
    background: linear-gradient(135deg, rgba(42, 96, 255, 0.22), rgba(117, 77, 255, 0.16));
    border: 1px solid color-mix(in srgb, var(--accent) 24%, transparent);
  }

  .welcome-action-card__copy {
    display: grid;
    gap: 0.55rem;
  }

  h3 {
    margin: 0;
    font-size: 1.08rem;
    letter-spacing: -0.03em;
  }

  p {
    margin: 0;
    color: var(--muted);
    line-height: 1.65;
  }

  .welcome-action-card__meta {
    width: fit-content;
    padding: 0.4rem 0.72rem;
    border-radius: 999px;
    font-size: 0.78rem;
    color: var(--ink-soft);
    border: 1px solid var(--line);
    background: rgba(255, 255, 255, 0.03);
  }

  .welcome-action-card__cta {
    width: fit-content;
    min-height: 46px;
    padding: 0.8rem 1rem;
    border-radius: 14px;
    border: 1px solid color-mix(in srgb, var(--accent) 48%, transparent);
    background: rgba(18, 35, 84, 0.72);
    color: var(--accent);
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
  }
</style>
