<script lang="ts">
  import AppLogo from '$components/AppLogo.svelte';

  interface Props {
    eyebrow?: string;
    title: string;
    subtitle?: string;
    alternateHref?: string;
    alternateLabel?: string;
    alternateCta?: string;
    children?: import('svelte').Snippet;
  }

  let {
    eyebrow = 'Access',
    title,
    subtitle = '',
    alternateHref = '/auth/sign-up',
    alternateLabel = 'Need an account?',
    alternateCta = 'Sign up',
    children
  }: Props = $props();
</script>

<section class="public-auth-shell">
  <aside class="public-auth-copy">
    <div class="public-auth-links">
      <a href="/privacy">Privacy</a>
      <a href="/terms">Terms</a>
      <a href="/billing">Billing</a>
      <a href="/contact">Contact</a>
    </div>

    <div class="marketing-brand__stack">
      <AppLogo size="sm" alt="Deck AIStack logo" />
      <div>
        <strong>Deck AIStack</strong>
        <p>Built for diligence adaptation, not generic slide generation.</p>
      </div>
    </div>
    <p class="muted">Reviewable AI editing, structured deck blocks, audience-specific recommendations, and export-ready investor workflows.</p>
  </aside>

  <main class="panel public-auth-panel">
    <div class="eyebrow">{eyebrow}</div>
    <h1>{title}</h1>
    {#if subtitle}
      <p class="muted public-auth-intro">{subtitle}</p>
    {/if}
    {@render children?.()}
    <p class="public-auth-alternate">{alternateLabel} <a href={alternateHref}>{alternateCta}</a></p>
  </main>

  <aside class="public-auth-boundary">
    <strong>Secure workspace access</strong>
    <p class="muted">Auth flows use the secure session bridge and connect to Deck AIStack account services when the API URL is configured.</p>
  </aside>
</section>

<style>
  .public-auth-links {
    display: flex;
    flex-wrap: wrap;
    gap: 0.85rem;
    margin-bottom: 1rem;
    color: var(--muted);
    font-size: 0.82rem;
  }
</style>
