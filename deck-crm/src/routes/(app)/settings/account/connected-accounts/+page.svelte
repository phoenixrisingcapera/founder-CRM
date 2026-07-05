<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import PageHeader from '$components/PageHeader.svelte';
  import type { ConnectedAccountProvider, UserSettingsSnapshot } from '$types/domain';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  function initialSettings() {
    return data.settings;
  }

  let settings = $state<UserSettingsSnapshot>(initialSettings());
  let busyProvider = $state<ConnectedAccountProvider | null>(null);
  let requestError = $state('');

  const providerMeta: Record<
    ConnectedAccountProvider,
    { label: string; detail: string; origin: 'connected_accounts_page' }
  > = {
    microsoft: {
      label: 'Microsoft',
      detail: 'Use Microsoft identity, calendar, mail, and work profile signals to enrich user settings and deck context.',
      origin: 'connected_accounts_page'
    },
    linkedin: {
      label: 'LinkedIn',
      detail: 'Use LinkedIn professional profile data, headline, skills, and company profile hints to enrich user settings.',
      origin: 'connected_accounts_page'
    }
  };

  const providerOrder: ConnectedAccountProvider[] = ['microsoft', 'linkedin'];

  function getAccount(provider: ConnectedAccountProvider) {
    return settings.connectedAccounts.find((account) => account.provider === provider) ?? null;
  }

  async function connectProvider(provider: ConnectedAccountProvider) {
    busyProvider = provider;
    requestError = '';

    try {
      const response = await fetch('/api/settings/account/connected-accounts', {
        method: 'POST',
        headers: {
          'content-type': 'application/json'
        },
        body: JSON.stringify({
          provider,
          origin: providerMeta[provider].origin
        })
      });

      if (!response.ok) {
        requestError = `Could not connect ${providerMeta[provider].label}.`;
        return;
      }

      const payload = (await response.json()) as { settings: UserSettingsSnapshot };
      settings = payload.settings;
    } catch {
      requestError = `Could not connect ${providerMeta[provider].label}.`;
    } finally {
      busyProvider = null;
    }
  }
</script>

<AppShell
  title="Connected accounts"
  subtitle="These accounts drive global user settings, profile enrichment, and future agent context across the workspace."
  activeNav="connected-accounts"
  deckLabel="Account settings"
>
  <section class="section-stack app-content-narrow">
    <PageHeader
      eyebrow="Identity graph"
      title="Global user data sources"
      subtitle="Microsoft and LinkedIn connections enrich the user profile table and can later support smarter account-level defaults."
      aside={settings.profile?.displayName ?? settings.user.name}
    />

    {#if requestError}
      <div class="feedback error">{requestError}</div>
    {/if}

    <section class="accounts-grid">
      <section class="panel profile-card">
        <div class="eyebrow">User data table</div>
        <h2>{settings.profile?.displayName ?? settings.user.name}</h2>
        <dl class="profile-grid">
          <div><dt>Email</dt><dd>{settings.user.email}</dd></div>
          <div><dt>Headline</dt><dd>{settings.profile?.headline ?? 'Not provided'}</dd></div>
          <div><dt>Company</dt><dd>{settings.profile?.companyName ?? 'Not provided'}</dd></div>
          <div><dt>Job title</dt><dd>{settings.profile?.jobTitle ?? 'Not provided'}</dd></div>
          <div><dt>Department</dt><dd>{settings.profile?.department ?? 'Not provided'}</dd></div>
          <div><dt>Timezone</dt><dd>{settings.profile?.timezone ?? 'Not provided'}</dd></div>
          <div><dt>LinkedIn URL</dt><dd>{settings.profile?.linkedinProfileUrl ?? 'Not connected'}</dd></div>
          <div><dt>Work email</dt><dd>{settings.profile?.workEmail ?? 'Not connected'}</dd></div>
        </dl>
      </section>

      <section class="panel account-list">
        <div class="eyebrow">Connected accounts</div>
        {#each settings.connectedAccounts as account}
          <article class="account-card">
            <div class="topline">
              <div>
                <strong>{providerMeta[account.provider].label}</strong>
                <p class="muted">{providerMeta[account.provider].detail}</p>
              </div>
              <span class={`status ${account.status}`}>{account.status.replace('_', ' ')}</span>
            </div>

            <dl class="account-grid">
              <div><dt>External identity</dt><dd>{account.externalDisplayName ?? 'Unknown'}</dd></div>
              <div><dt>External email</dt><dd>{account.externalEmail ?? 'Not provided'}</dd></div>
              <div><dt>API scopes</dt><dd>{account.scopes.join(', ')}</dd></div>
              <div><dt>Last synced</dt><dd>{account.lastSyncedAt ? new Date(account.lastSyncedAt).toLocaleString() : 'Never'}</dd></div>
              <div><dt>Token</dt><dd>{account.accessTokenMasked ?? 'Not stored'}</dd></div>
              <div><dt>Refresh token</dt><dd>{account.refreshTokenStored ? 'Stored' : 'Not stored'}</dd></div>
            </dl>

            <div class="actions">
              <button
                class="button secondary"
                type="button"
                disabled={busyProvider === account.provider}
                onclick={() => connectProvider(account.provider)}
              >
                {busyProvider === account.provider ? 'Syncing...' : 'Sync now'}
              </button>
              <button
                class="ghost"
                type="button"
                disabled={busyProvider === account.provider}
                onclick={() => connectProvider(account.provider)}
              >
                {busyProvider === account.provider ? 'Connecting...' : 'Reconnect'}
              </button>
            </div>
          </article>
        {/each}

        <article class="account-card connect-card">
          <strong>Connect another account</strong>
          <p class="muted">Add Microsoft or LinkedIn here so the user profile table stays globally enriched across Deck AIStack.</p>
          <div class="actions">
            {#each providerOrder as provider}
              <button
                class={provider === 'microsoft' ? 'button' : 'ghost'}
                type="button"
                disabled={busyProvider === provider}
                onclick={() => connectProvider(provider)}
              >
                {busyProvider === provider
                  ? `Connecting ${providerMeta[provider].label}...`
                  : getAccount(provider)
                    ? `Reconnect ${providerMeta[provider].label}`
                    : `Connect ${providerMeta[provider].label}`}
              </button>
            {/each}
          </div>
        </article>
      </section>
    </section>
  </section>
</AppShell>

<style>
  .accounts-grid {
    display: grid;
    grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
    gap: 1rem;
  }

  .profile-card,
  .account-list {
    padding: 1.2rem;
    display: grid;
    gap: 1rem;
    align-content: start;
  }

  h2 {
    margin: 0;
  }

  .profile-grid,
  .account-grid {
    display: grid;
    gap: 0.9rem;
    margin: 0;
  }

  .profile-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  dt {
    color: var(--muted);
    font-size: 0.82rem;
  }

  dd {
    margin: 0.25rem 0 0;
    font-weight: 600;
    word-break: break-word;
  }

  .account-card {
    border: 1px solid var(--line);
    border-radius: 20px;
    background: rgba(255,255,255,0.03);
    padding: 1rem;
    display: grid;
    gap: 0.9rem;
  }

  .topline,
  .actions {
    display: flex;
    justify-content: space-between;
    gap: 0.85rem;
    align-items: start;
    flex-wrap: wrap;
  }

  .status {
    border-radius: 999px;
    padding: 0.45rem 0.75rem;
    border: 1px solid var(--line);
    text-transform: capitalize;
  }

  .status.connected {
    color: var(--success);
    border-color: rgba(34, 197, 94, 0.28);
    background: rgba(34, 197, 94, 0.08);
  }

  .status.syncing {
    color: var(--accent);
  }

  .status.needs_reauth {
    color: var(--warn);
  }

  .ghost {
    min-height: 48px;
    border-radius: 14px;
    border: 1px solid var(--line);
    background: transparent;
    color: var(--ink-strong);
    padding: 0.75rem 1rem;
  }

  .connect-card {
    border-style: dashed;
  }

  .feedback {
    border-radius: 16px;
    padding: 0.95rem 1rem;
    border: 1px solid rgba(239, 68, 68, 0.22);
    background: rgba(127, 29, 29, 0.28);
    color: #fecaca;
  }

  @media (max-width: 980px) {
    .accounts-grid,
    .profile-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
