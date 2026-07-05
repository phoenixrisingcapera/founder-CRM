<script lang="ts">
  import ThemeToggle from '$lib/components/ThemeToggle.svelte';

  const links = [
    { href: '/privacy', label: 'Privacy' },
    { href: '/terms', label: 'Terms' },
    { href: '/contact', label: 'Contact' },
    { href: '/auth/sign-in', label: 'Sign in' }
  ];
</script>

<div class="marketing-utility">
  <div class="marketing-utility__inner">
    <nav class="marketing-utility__links">
      {#each links as link}
        <a href={link.href}>{link.label}</a>
      {/each}
    </nav>
    <div class="marketing-utility__actions">
      <span class="marketing-trust">
        <span class="marketing-trust__dot"></span>
        Marketing surface
      </span>
      <ThemeToggle />
    </div>
  </div>
</div>

<style>
  .marketing-utility__links a {
    color: rgba(223, 232, 248, 0.78);
    transition: color 160ms ease;
  }

  .marketing-utility__links a:hover {
    color: #f8fbff;
  }

  .marketing-trust {
    padding: 0.3rem 0.65rem;
    border-radius: 999px;
    border: 1px solid rgba(106, 132, 196, 0.22);
    background: rgba(255, 255, 255, 0.04);
    color: #eef4ff;
  }
</style>
