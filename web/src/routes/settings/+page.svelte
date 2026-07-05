<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { getSettings, saveApiKey, signOut } from '$lib/api';
  import { session } from '$lib/stores/session';
  import type { SettingsSummary } from '$lib/types';

  let settings: SettingsSummary | null = null;
  let provider = 'openai';
  let apiKey = '';
  let error = '';

  onMount(async () => {
    try {
      settings = await getSettings();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not load settings.';
    }
  });

  async function persistKey() {
    try {
      settings = await saveApiKey({ provider, api_key: apiKey });
      apiKey = '';
      error = '';
    } catch (err) {
      error = err instanceof Error ? err.message : 'Could not save API key.';
    }
  }

  async function logout() {
    await signOut();
    session.set(null);
    goto('/auth');
  }
</script>

<div class="page-grid">
  <section class="panel">
    <div class="eyebrow">Settings</div>
    <h1 style="margin:0.4rem 0 0.75rem 0;">Security and workspace controls</h1>
    <p class="muted">Persist provider keys only when `CRM_ENCRYPTION_KEY` is configured. Otherwise use session-only keys in Deck Assistant.</p>
  </section>

  <section class="panel">
    <h2 style="margin-top:0;">Provider keys</h2>
    <div class="form-grid">
      <select class="select" bind:value={provider}><option value="openai">OpenAI</option><option value="openrouter">OpenRouter</option></select>
      <input class="field" bind:value={apiKey} placeholder="Provider API key" />
    </div>
    <div style="display:flex; justify-content:space-between; gap:1rem; align-items:center; margin-top:1rem;">
      <div class="muted">{error || (settings ? `Exports are ${settings.exports_enabled ? 'enabled' : 'disabled'} for this workspace.` : '')}</div>
      <button class="button" on:click={persistKey} disabled={!apiKey}>Save encrypted key</button>
    </div>
    {#if settings}
      <div style="margin-top:1rem;">
        {#if settings.api_keys.length}
          <table class="table"><thead><tr><th>Provider</th><th>Status</th></tr></thead><tbody>{#each settings.api_keys as item}<tr><td>{item.provider}</td><td>{item.configured ? 'Configured' : 'Missing'}</td></tr>{/each}</tbody></table>
        {:else}
          <div class="muted">No persisted keys yet.</div>
        {/if}
      </div>
    {/if}
  </section>

  <section class="panel">
    <h2 style="margin-top:0;">Session</h2>
    <p class="muted">Sign out to clear the current workspace session on this device.</p>
    <button class="button secondary" on:click={logout}>Sign out</button>
  </section>
</div>
