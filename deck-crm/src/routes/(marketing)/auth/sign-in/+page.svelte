<script lang="ts">
  import { goto } from '$app/navigation';
  import PublicAuthShell from '$components/PublicAuthShell.svelte';
  import AuthSuccessLoader from '$lib/components/AuthSuccessLoader.svelte';
  import { signIn } from '$lib/api/auth';

  let form = $state({
    email: '',
    password: ''
  });
  let submitting = $state(false);
  let errorMessage = $state('');
  let redirecting = $state(false);

  const redirectSteps = ['Validate session', 'Prepare testing workspace', 'Open welcome'];

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    submitting = true;
    errorMessage = '';
    redirecting = false;

    try {
      const email = form.email.trim().toLowerCase();
      const password = form.password;

      if (!email || !password) {
        errorMessage = 'Email and password are required.';
        return;
      }

      if (password.length < 8) {
        errorMessage = 'Password must be at least 8 characters.';
        return;
      }

      const response = await signIn({ email, password });
      redirecting = true;
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await goto(response.nextUrl);
    } catch (error) {
      redirecting = false;
      errorMessage = error instanceof Error ? error.message : 'Could not sign in.';
    } finally {
      submitting = false;
    }
  }
</script>

<PublicAuthShell
  eyebrow="Sign in"
  title="Access your deck workspace"
  subtitle="Sign in to continue into the Smart Deck intake and the signed-in workspace shell."
  alternateHref="/auth/sign-up"
  alternateLabel="Need an account?"
  alternateCta="Sign up"
>
  <form class="auth-card" onsubmit={handleSubmit}>
    <label>
      <span>Email</span>
      <input type="email" bind:value={form.email} autocomplete="email" required />
    </label>
    <label>
      <span>Password</span>
      <input type="password" bind:value={form.password} autocomplete="current-password" required minlength="8" />
    </label>
    {#if errorMessage}
      <p class="error-message">{errorMessage}</p>
    {/if}
    <button class="button submit" type="submit" disabled={submitting}>
      {submitting ? 'Signing in...' : 'Sign in'}
    </button>
  </form>
</PublicAuthShell>

<AuthSuccessLoader
  open={redirecting}
  overlay={true}
  title="Signed in"
  subtitle="Preparing your workspace before the redirect."
  statusLabel="Testing approved"
  notice="You are approved for testing. Redirecting to welcome..."
  steps={redirectSteps}
/>

<style>
  .auth-card {
    display: grid;
    gap: 1rem;
  }

  label {
    display: grid;
    gap: 0.45rem;
  }

  input {
    border-radius: var(--radius-sm);
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.03);
    color: var(--ink);
    padding: 0.85rem;
  }

  .submit {
    display: grid;
    place-items: center;
    min-height: 54px;
  }

  .error-message {
    margin: 0;
    color: var(--danger);
  }
</style>
