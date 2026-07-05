<script lang="ts">
  import { goto } from '$app/navigation';
  import { createDemoSession, signIn, signUp } from '$lib/api';
  import { session } from '$lib/stores/session';

  let mode: 'signin' | 'signup' = 'signin';
  let fullName = '';
  let email = '';
  let password = '';
  let error = '';
  let saving = false;

  async function submit() {
    saving = true;
    error = '';
    try {
      const currentSession =
        mode === 'signup'
          ? await signUp({ full_name: fullName, email, password })
          : await signIn({ email, password });
      session.set(currentSession);
      goto('/dashboard');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Authentication failed.';
    } finally {
      saving = false;
    }
  }

  async function useDemo() {
    saving = true;
    error = '';
    try {
      const currentSession = await createDemoSession();
      session.set(currentSession);
      goto('/dashboard');
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not start demo workspace.';
    } finally {
      saving = false;
    }
  }
</script>

<div class="page-grid" style="max-width:42rem; margin:0 auto;">
  <section class="panel">
    <div class="eyebrow">AiStack Founder CRM</div>
    <h1 class="display-title" style="font-size:2.6rem;">Founder-owned fundraising operations.</h1>
    <p class="muted">Real sign-in, workspace isolation, and optional low-cost AI through your own provider key.</p>
  </section>

  <section class="panel">
    <div style="display:flex; gap:0.75rem; margin-bottom:1rem;">
      <button class="button {mode === 'signin' ? '' : 'secondary'}" on:click={() => (mode = 'signin')}>Sign in</button>
      <button class="button {mode === 'signup' ? '' : 'secondary'}" on:click={() => (mode = 'signup')}>Create account</button>
    </div>
    <div class="form-grid">
      {#if mode === 'signup'}
        <input class="field" bind:value={fullName} placeholder="Full name" />
      {/if}
      <input class="field" bind:value={email} placeholder="Email" type="email" />
      <input class="field" bind:value={password} placeholder="Password" type="password" />
    </div>
    <div style="display:flex; justify-content:space-between; gap:1rem; align-items:center; margin-top:1rem;">
      <div class="muted">{error}</div>
      <div style="display:flex; gap:0.75rem;">
        <button class="button secondary" on:click={useDemo} disabled={saving}>Demo workspace</button>
        <button class="button" on:click={submit} disabled={saving || !email || !password || (mode === 'signup' && !fullName)}>
          {saving ? 'Working...' : mode === 'signup' ? 'Create account' : 'Sign in'}
        </button>
      </div>
    </div>
  </section>
</div>
