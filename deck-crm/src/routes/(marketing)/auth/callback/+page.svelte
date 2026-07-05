<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import AuthSuccessLoader from '$lib/components/AuthSuccessLoader.svelte';
  import { completeAuthCallback } from '$lib/api/auth';

  let errorMessage = $state('');

  const steps = [
    'Read callback payload',
    'Bridge auth into the session layer',
    'Redirect to the signed-in success state'
  ];

  async function finishCallback() {
    try {
      const response = await completeAuthCallback({
        email: page.url.searchParams.get('email') ?? undefined,
        name: page.url.searchParams.get('name') ?? undefined
      });

      await goto(response.nextUrl);
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Could not complete callback.';
    }
  }

  $effect(() => {
    finishCallback();
  });
</script>

<section class="callback-page">
  <AuthSuccessLoader
    title="Completing sign-in callback"
    subtitle="Validating the response and preparing your Deck AIStack session..."
    {steps}
    {errorMessage}
  />

  {#if errorMessage}
    <a class="button secondary" href="/auth/sign-in">Back to sign in</a>
  {/if}
</section>

<style>
  .callback-page {
    width: min(100%, 720px);
    margin: 0 auto;
    display: grid;
    gap: 1rem;
  }
</style>
