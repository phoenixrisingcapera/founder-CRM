<script lang="ts">
  import AppLogo from '$components/AppLogo.svelte';

  export let currentPath = '/';

  const nav = [
    { href: '/', label: 'Product' },
    { href: '/vcs', label: 'For VCs' },
    { href: '/pricing', label: 'Pricing' },
    { href: '/about', label: 'About' },
    { href: '/contact', label: 'Contact' }
  ];

  function isActive(href: string) {
    return currentPath === href;
  }
</script>

<header class="header">
  <a class="brand" href="/">
    <AppLogo class="header-logo" alt="Deck AIStack logo" />
    <div>
      <strong>Deck AIStack</strong>
      <p>AI diligence deck adaptation</p>
    </div>
  </a>

  <nav class="links">
    {#each nav as item}
      <a href={item.href} class:active={isActive(item.href)}>{item.label}</a>
    {/each}
  </nav>

  <div class="actions">
    <a class="ghost" href="/auth/sign-in">Sign in</a>
    <a class="button" href="/auth/sign-up">Show interest</a>
  </div>
</header>

<style>
  .header {
    width: min(100% - 2rem, 1200px);
    margin: 0 auto;
    padding: 1rem 1.25rem;
    border: 1px solid var(--line);
    border-radius: 999px;
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    background: rgba(8, 20, 45, 0.72);
    backdrop-filter: blur(18px);
  }

  :global([data-theme="light"]) .header {
    background: rgba(255, 255, 255, 0.78);
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 0.8rem;
  }

  :global(.header-logo) {
    width: 46px;
    height: 46px;
    border-radius: 15px;
  }

  .brand p {
    margin: 0.18rem 0 0;
    font-size: 0.84rem;
    color: var(--muted);
  }

  .links,
  .actions {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .links a {
    color: var(--ink-soft);
    padding: 0.55rem 0;
  }

  .links a.active {
    color: var(--ink-strong);
  }

  .ghost {
    padding: 0.8rem 1rem;
    border-radius: 999px;
    border: 1px solid var(--line);
    color: var(--ink-soft);
  }

  @media (max-width: 1100px) {
    .header {
      border-radius: 24px;
      flex-direction: column;
      align-items: start;
    }
  }
</style>
