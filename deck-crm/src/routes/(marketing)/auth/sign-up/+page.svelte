<script lang="ts">
  import { goto } from '$app/navigation';
  import PublicAuthShell from '$components/PublicAuthShell.svelte';
  import AuthSuccessLoader from '$lib/components/AuthSuccessLoader.svelte';
  import { signUp } from '$lib/api/auth';

  let form = $state({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    companyName: '',
    acceptedTerms: false
  });
  let submitting = $state(false);
  let errorMessage = $state('');
  let successMessage = $state('');
  let redirecting = $state(false);

  const redirectSteps = ['Create account', 'Mark testing access', 'Open welcome'];

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    submitting = true;
    errorMessage = '';
    successMessage = '';
    redirecting = false;

    try {
      const name = form.name.trim();
      const email = form.email.trim().toLowerCase();
      const password = form.password;
      const confirmPassword = form.confirmPassword;
      const companyName = form.companyName.trim();

      if (!name || !email || !password || !confirmPassword) {
        errorMessage = 'Name, email, password, and confirmation are required.';
        return;
      }

      if (password !== confirmPassword) {
        errorMessage = 'Passwords do not match.';
        return;
      }

      if (!form.acceptedTerms) {
        errorMessage = 'You must accept the terms to create an account.';
        return;
      }

      const response = await signUp({
        name,
        email,
        password,
        companyName: companyName || undefined,
        acceptedTerms: form.acceptedTerms
      });
      successMessage = response.workspace
        ? `Workspace ${response.workspace.name} created. Redirecting...`
        : 'Account created. Redirecting...';
      redirecting = true;
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await goto(response.nextUrl);
    } catch (error) {
      redirecting = false;
      errorMessage = error instanceof Error ? error.message : 'Could not create account.';
    } finally {
      submitting = false;
    }
  }
</script>

<PublicAuthShell
  eyebrow="Sign up"
  title="Create a Deck AIStack workspace"
  subtitle="Create a normal user workspace, then continue to welcome to upload a deck, load URL branding, or load logo branding."
  alternateHref="/auth/sign-in"
  alternateLabel="Already have an account?"
  alternateCta="Sign in"
>
  <form class="auth-card" onsubmit={handleSubmit}>
    <label>
      <span>Name</span>
      <input bind:value={form.name} placeholder="Avery Chen" autocomplete="name" required minlength="2" />
    </label>
    <label>
      <span>Email</span>
      <input type="email" bind:value={form.email} placeholder="analyst@deck.aistack.codes" autocomplete="email" required />
    </label>
    <label>
      <span>Password</span>
      <input type="password" bind:value={form.password} placeholder="Create a password" autocomplete="new-password" required minlength="8" />
    </label>
    <label>
      <span>Confirm password</span>
      <input type="password" bind:value={form.confirmPassword} placeholder="Confirm password" autocomplete="new-password" required minlength="8" />
    </label>
    <label>
      <span>Company name</span>
      <input bind:value={form.companyName} placeholder="Northline Ventures" autocomplete="organization" />
    </label>
    <label class="terms-row">
      <input type="checkbox" bind:checked={form.acceptedTerms} required />
      <span>I agree to the Deck AIStack terms and privacy policy.</span>
    </label>
    {#if errorMessage}
      <p class="error-message">{errorMessage}</p>
    {/if}
    {#if successMessage}
      <p class="success-message">{successMessage}</p>
    {/if}
    <button class="button submit" type="submit" disabled={submitting}>
      {submitting ? 'Creating account...' : 'Create account'}
    </button>
  </form>
</PublicAuthShell>

<AuthSuccessLoader
  open={redirecting}
  overlay={true}
  title="Account created"
  subtitle="Preparing testing access before the redirect."
  statusLabel="Testing mode"
  notice="You are in testing mode until your account is approved."
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
    width: 100%;
    min-width: 0;
    border-radius: var(--radius-sm);
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.03);
    color: var(--ink);
    padding: 0.85rem;
    font-size: 1rem;
  }

  input[type='checkbox'] {
    width: 18px;
    height: 18px;
    padding: 0;
    accent-color: var(--accent);
  }

  .terms-row {
    grid-template-columns: 18px 1fr;
    align-items: start;
    gap: 0.65rem;
    color: var(--muted);
    font-size: 0.92rem;
    line-height: 1.35;
  }

  .submit {
    display: grid;
    place-items: center;
    min-height: 54px;
    width: 100%;
  }

  .error-message {
    margin: 0;
    color: var(--danger);
  }

  .success-message {
    margin: 0;
    color: #33d69f;
  }

  @media (max-width: 520px) {
    .auth-card {
      gap: 0.85rem;
    }

    input {
      min-height: 48px;
    }
  }

</style>
