<script lang="ts">
  import CTASection from '$lib/components/marketing/CTASection.svelte';
  import ComparisonSection from '$lib/components/marketing/ComparisonSection.svelte';
  import ForVCsSection from '$lib/components/marketing/ForVCsSection.svelte';
  import HeroSection from '$lib/components/marketing/HeroSection.svelte';
  import HowItWorksSection from '$lib/components/marketing/HowItWorksSection.svelte';
  import ProductPreviewSection from '$lib/components/marketing/ProductPreviewSection.svelte';
  import ShowInterestForm from '$lib/components/marketing/ShowInterestForm.svelte';
  import UseCaseStrip from '$lib/components/marketing/UseCaseStrip.svelte';
</script>

<div class="marketing-page home-page">
  <HeroSection />
  <HowItWorksSection />
  <UseCaseStrip />
  <ComparisonSection />
  <ForVCsSection />
  <ProductPreviewSection />
  <ShowInterestForm sourcePage="home" />
  <CTASection />
</div>

<style>
  .home-page {
    display: grid;
    gap: 1.1rem;
  }
</style>
