<footer class="footer">
  <div>
    <strong>Deck AIStack</strong>
    <p>Investor-grade adaptation for existing decks, not generic slide generation.</p>
  </div>

  <nav>
    <a href="/privacy">Privacy</a>
    <a href="/terms">Terms</a>
    <a href="/contact">Contact</a>
    <a href="/auth/sign-in">Sign in</a>
  </nav>
</footer>

<style>
  .footer {
    width: min(100% - 2rem, 1200px);
    margin: 0 auto;
    padding: 2rem 0 3rem;
    display: flex;
    justify-content: space-between;
    gap: 1.25rem;
    align-items: end;
    color: var(--muted);
  }

  .footer p {
    margin: 0.35rem 0 0;
    max-width: 480px;
  }

  nav {
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
  }

  @media (max-width: 840px) {
    .footer {
      flex-direction: column;
      align-items: start;
    }
  }
</style>
