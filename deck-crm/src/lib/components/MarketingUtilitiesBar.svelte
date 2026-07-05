<script lang="ts">
  const links = [
    { href: '/privacy', label: 'Privacy' },
    { href: '/terms', label: 'Terms' },
    { href: '/pricing', label: 'Pricing' },
    { href: '/contact', label: 'Contact' }
  ];
</script>

<div class="utilities">
  <nav>
    {#each links as link}
      <a href={link.href}>{link.label}</a>
    {/each}
  </nav>
  <div class="status">
    <span class="dot"></span>
    <span>Public site</span>
  </div>
</div>

<style>
  .utilities {
    width: min(100% - 2rem, 1200px);
    margin: 0 auto;
    padding: 0.8rem 0 0;
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
    color: var(--muted);
    font-size: 0.84rem;
  }

  nav,
  .status {
    display: flex;
    gap: 0.85rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .dot {
    width: 0.62rem;
    height: 0.62rem;
    border-radius: 999px;
    background: var(--accent);
    box-shadow: 0 0 0 6px rgba(24, 200, 255, 0.12);
  }

  @media (max-width: 720px) {
    .utilities {
      flex-direction: column;
      align-items: start;
    }
  }
</style>
