<script lang="ts">
  import CTASection from '$lib/components/marketing/CTASection.svelte';
  import MarketingCardGrid from '$lib/components/marketing/MarketingCardGrid.svelte';
  import MarketingPageHero from '$lib/components/marketing/MarketingPageHero.svelte';

  const vcFlows = [
    {
      title: 'IC preparation',
      body: 'Sharpen claims, expose missing proof, and move founder decks into a partner-review state faster.'
    },
    {
      title: 'Partner review',
      body: 'Prepare controlled variations for different reviewers without losing the original deck context.'
    },
    {
      title: 'Strategic investor versions',
      body: 'Prepare audience-aware deck iterations for board, LP, strategic, or advisory review settings.'
    }
  ];

  const reasons = [
    {
      title: 'Not a blank slide tool',
      body: 'The product assumes a deck already exists and needs to be inspected, improved, and adapted with control.'
    },
    {
      title: 'Findings tied to structure',
      body: 'Diligence findings, suggestions, and edits stay linked to slides and blocks instead of floating outside the deck.'
    },
    {
      title: 'Reviewable AI output',
      body: 'Every AI change is surfaced for acceptance, rejection, or revision before the deck is changed.'
    }
  ];
</script>

<div class="marketing-page">
  <MarketingPageHero
    eyebrow="For VCs"
    title="Built for investment teams, IC preparation, and partner review."
    body="Deck AIStack helps VC teams turn founder decks into classified, reviewable diligence material without flattening the deck into one prompt."
    secondaryBody="Use cases include IC prep, partner review, strategic investor versions, and controlled Smart Edit review before export."
    highlights={[
      { label: 'Use case', value: 'IC and partner review' },
      { label: 'Adaptation mode', value: 'Audience-specific iterations' },
      { label: 'Review rule', value: 'No silent overwrites' },
      { label: 'Primary asset', value: 'Existing founder deck' }
    ]}
  />

  <MarketingCardGrid
    eyebrow="VC workflows"
    title="Where the product fits in the investment process"
    body="The platform is designed to support investor-side work without losing the deck’s original story and evidence structure."
    items={vcFlows}
  />

  <MarketingCardGrid
    eyebrow="Why it matters"
    title="Why this is different from generic AI presentation software"
    items={reasons}
  />

  <CTASection />
</div>

<style>
  .marketing-page {
    display: grid;
    gap: 1.1rem;
  }
</style>
