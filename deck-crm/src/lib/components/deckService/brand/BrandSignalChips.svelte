<script lang="ts">
  import type { BrandProfile, BrandStatus } from '$lib/types/deckService-brand';

  let {
    brandProfile = null,
    status = 'idle',
    hasWebsiteInput = false,
    hasLogoInput = false,
    hasDeckInput = false
  }: {
    brandProfile?: BrandProfile | null;
    status?: BrandStatus;
    hasWebsiteInput?: boolean;
    hasLogoInput?: boolean;
    hasDeckInput?: boolean;
  } = $props();

  const confidence = $derived.by(() => {
    if (typeof brandProfile?.confidenceScore !== 'number') return 'Confidence -';
    return `Confidence ${brandProfile.confidenceScore.toFixed(2)}`;
  });

  const websiteActive = $derived(Boolean(brandProfile?.companyWebsiteUrl || hasWebsiteInput));
  const logoActive = $derived(Boolean(brandProfile?.logoUrl || brandProfile?.logoStorageKey || hasLogoInput));
  const deckActive = $derived(hasDeckInput || brandProfile?.sourceMode === 'deck' || brandProfile?.source === 'deck');
  const extracting = $derived(status === 'extracting');
</script>

<section class="brand-signal-chips" data-component-tag="brand-signal-chips" aria-label="Brand signals and source evidence">
  <strong>Brand signals / source evidence</strong>
  <div>
    <span class:brand-signal-chips__active={websiteActive}>Website</span>
    <span class:brand-signal-chips__active={logoActive}>Logo</span>
    <span class:brand-signal-chips__active={deckActive}>Deck</span>
    <span class:brand-signal-chips__active={brandProfile?.confidenceScore}>{confidence}</span>
  </div>
  {#if extracting}
    <progress aria-label="Extracting brand signals" max="100" value="42"></progress>
  {/if}
</section>

<style>
  .brand-signal-chips {
    display: grid;
    gap: 0.6rem;
  }

  .brand-signal-chips > strong {
    color: var(--brand-card-text);
    font-size: 0.88rem;
  }

  .brand-signal-chips div {
    display: flex;
    flex-wrap: wrap;
    gap: 0.45rem;
  }

  .brand-signal-chips span {
    border: 1px solid var(--brand-card-border);
    border-radius: 999px;
    background: var(--brand-card-muted-surface);
    color: var(--brand-card-text-muted);
    padding: 0.42rem 0.62rem;
    font-size: 0.78rem;
    font-weight: 700;
  }

  .brand-signal-chips__active {
    border-color: color-mix(in srgb, var(--brand-card-accent) 42%, var(--brand-card-border));
    color: var(--brand-card-text);
  }

  progress {
    width: 100%;
    height: 0.38rem;
    border: 0;
    border-radius: 999px;
    background: var(--brand-card-muted-surface);
  }

  progress::-webkit-progress-bar {
    border-radius: 999px;
    background: var(--brand-card-muted-surface);
  }

  progress::-webkit-progress-value {
    border-radius: 999px;
    background: var(--brand-card-accent);
  }

  progress::-moz-progress-bar {
    border-radius: 999px;
    background: var(--brand-card-accent);
  }
</style>
