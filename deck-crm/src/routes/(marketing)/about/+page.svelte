<script lang="ts">
  import CTASection from '$lib/components/marketing/CTASection.svelte';
  import MarketingCardGrid from '$lib/components/marketing/MarketingCardGrid.svelte';
  import MarketingPageHero from '$lib/components/marketing/MarketingPageHero.svelte';

  const pillars = [
    {
      title: 'Deck-first system',
      body: 'The uploaded deck remains the source of truth. Deck AIStack adapts from that material instead of starting from a blank prompt.'
    },
    {
      title: 'Block-level intelligence',
      body: 'Slides become structured editable blocks that can be classified, reviewed, and traced through the workflow.'
    },
    {
      title: 'Review before apply',
      body: 'Smart Edit, adaptation, and analysis outputs are presented as reviewable suggestions rather than silent overwrites.'
    }
  ];

  const workflow = [
    {
      title: 'Parse and structure',
      body: 'Upload PDF or PowerPoint material and turn the deck into reviewable slides, sections, and source-linked context.'
    },
    {
      title: 'Classify and analyse',
      body: 'Classify each block, identify diligence gaps, and generate findings tied to the real deck structure.'
    },
    {
      title: 'Adapt and export',
      body: 'Create audience-specific versions, review edits, and export investor-ready outputs once changes are approved.'
    }
  ];
</script>

<div class="marketing-page">
  <MarketingPageHero
    eyebrow="About"
    title="Deck AIStack is built for diligence adaptation, not generic slide generation."
    body="The platform is designed for venture, advisory, and strategic review workflows where the uploaded deck remains the source of truth and every AI suggestion must be reviewable before it changes content."
    secondaryBody="That means structured slides, editable blocks, classification, analysis, audience adaptation, Smart Edit, change review, and export all operate as one controlled workflow."
    highlights={[
      { label: 'Source of truth', value: 'Uploaded deck' },
      { label: 'AI behaviour', value: 'Reviewable suggestions' },
      { label: 'Primary users', value: 'VC, advisory, investment' },
      { label: 'Output style', value: 'Investor-grade adaptation' }
    ]}
  />

  <MarketingCardGrid
    eyebrow="Core principles"
    title="What the product is actually designed to do"
    body="Deck AIStack is opinionated about reviewability, provenance, and investor workflow control."
    items={pillars}
  />

  <MarketingCardGrid
    eyebrow="Workflow"
    title="One controlled system from upload to export"
    body="The product is shaped as a connected operational flow, not as isolated AI features."
    items={workflow}
  />

  <CTASection />
</div>

<style>
  .marketing-page {
    display: grid;
    gap: 1.1rem;
  }
</style>
