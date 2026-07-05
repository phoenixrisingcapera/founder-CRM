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
  let showReminder = $state(true);

  const providerMeta: Record<
    ConnectedAccountProvider,
    { label: string; summary: string; details: string; scopes: string }
  > = {
    microsoft: {
      label: 'Microsoft',
      summary: 'Sync work identity, work email, and organization signals.',
      details: 'Useful for company identity, deck ownership, and future calendar or document context.',
      scopes: 'User.Read, Mail.ReadBasic'
    },
    linkedin: {
      label: 'LinkedIn',
      summary: 'Sync public professional profile, headline, and company signals.',
      details: 'Useful for founder context, role detection, profile enrichment, and workspace defaults.',
      scopes: 'r_liteprofile, r_emailaddress'
    }
  };

  const providerOrder: ConnectedAccountProvider[] = ['microsoft', 'linkedin'];

  function getAccount(provider: ConnectedAccountProvider) {
    return settings.connectedAccounts.find((account) => account.provider === provider) ?? null;
  }

  function isConnected(provider: ConnectedAccountProvider) {
    const account = getAccount(provider);
    return !!account && account.status !== 'disconnected';
  }

  function connectedCount() {
    return providerOrder.filter((provider) => isConnected(provider)).length;
  }

  async function connectProvider(
    provider: ConnectedAccountProvider,
    origin: 'settings_page' | 'reminder_popup' = 'settings_page'
  ) {
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
          origin
        })
      });

      if (!response.ok) {
        requestError = `Could not connect ${providerMeta[provider].label}.`;
        return;
      }

      const payload = (await response.json()) as { settings: UserSettingsSnapshot };
      settings = payload.settings;
      showReminder = false;
    } catch {
      requestError = `Could not connect ${providerMeta[provider].label}.`;
    } finally {
      busyProvider = null;
    }
  }
</script>

<AppShell
  title="Profile and preferences"
  subtitle="Manage profile defaults, optional connected accounts, and the user-level identity graph that enriches Deck AIStack."
  activeNav="account-settings"
  deckLabel="Account settings"
>
  <section class="section-stack app-content-narrow">
    <PageHeader
      eyebrow="Settings"
      title="Workspace identity and account controls"
      subtitle="Connected accounts are optional. They improve profile enrichment and future agent context, but they never block access to the app."
      aside={`${connectedCount()} of ${providerOrder.length} account sources active`}
    />

    {#if requestError}
      <div class="feedback error">{requestError}</div>
    {/if}

    <section class="settings-grid">
      <section class="panel profile-card">
        <div class="eyebrow">Profile</div>
        <div class="profile-hero">
          <div class="avatar">
            {(settings.profile?.displayName ?? settings.user.name).slice(0, 2).toUpperCase()}
          </div>
          <div>
            <h2>{settings.profile?.displayName ?? settings.user.name}</h2>
            <p class="muted">{settings.profile?.headline ?? 'Investor profile details can be enriched from connected accounts.'}</p>
          </div>
        </div>

        <div class="field-grid">
          <label>
            <span>Name</span>
            <input value={settings.profile?.displayName ?? settings.user.name} />
          </label>
          <label>
            <span>Email</span>
            <input value={settings.user.email} />
          </label>
          <label>
            <span>Company</span>
            <input value={settings.profile?.companyName ?? 'Deck AIStack Capital'} />
          </label>
          <label>
            <span>Role</span>
            <input value={settings.profile?.jobTitle ?? 'Partner'} />
          </label>
        </div>

        <div class="panel-strip">
          <div class="data-point">
            <strong>{settings.profile?.timezone ?? 'Not set'}</strong>
            <span>Timezone</span>
          </div>
          <div class="data-point">
            <strong>{settings.profile?.department ?? 'Not set'}</strong>
            <span>Department</span>
          </div>
          <div class="data-point">
            <strong>{settings.profile?.workEmail ?? 'Not connected'}</strong>
            <span>Work email</span>
          </div>
        </div>

        <button class="button" type="button">Save changes</button>
      </section>

      <aside class="settings-column">
        <section class="panel summary-card">
          <div class="eyebrow">Connected sources</div>
          <div class="cardlet">
            <strong>Optional account graph</strong>
            <p class="muted">Add LinkedIn or Microsoft if you want richer user defaults, better company context, and cleaner founder or team signals later in the workflow.</p>
          </div>

          {#each providerOrder as provider}
            {@const account = getAccount(provider)}
            <article class="provider-card">
              <div class="provider-topline">
                <div>
                  <strong>{providerMeta[provider].label}</strong>
                  <p class="muted">{providerMeta[provider].summary}</p>
                </div>
                <span class={`status ${account?.status ?? 'disconnected'}`}>
                  {account?.status?.replace('_', ' ') ?? 'not connected'}
                </span>
              </div>

              <p class="detail">{providerMeta[provider].details}</p>
              <p class="scope-note">Scopes: {account?.scopes.join(', ') ?? providerMeta[provider].scopes}</p>

              <button
                class="ghost"
                type="button"
                disabled={busyProvider === provider}
                onclick={() => connectProvider(provider)}
              >
                {busyProvider === provider
                  ? `Connecting ${providerMeta[provider].label}...`
                  : account
                    ? `Reconnect ${providerMeta[provider].label}`
                    : `Connect ${providerMeta[provider].label}`}
              </button>
            </article>
          {/each}

          <a class="button secondary link-card" href="/settings/account/connected-accounts">
            Open connected accounts
          </a>
        </section>

        <section class="panel workspace-card">
          <div class="eyebrow">Workspace controls</div>
          <button class="ghost" type="button">Default brand</button>
          <button class="ghost" type="button">Notifications</button>
          <button class="ghost" type="button">Privacy posture</button>
          <button class="ghost" type="button">Session security</button>
        </section>
      </aside>
    </section>
  </section>

  {#if showReminder}
    <div class="modal-backdrop">
      <section class="reminder-modal panel">
        <div class="eyebrow">Optional setup</div>
        <h3>Connect your accounts whenever you want</h3>
        <p class="muted">
          You can link LinkedIn or Microsoft from Settings to enrich your user profile and future workspace defaults.
          It is optional and does not block the product workflow.
        </p>
        <div class="modal-actions">
          <button class="button" type="button" onclick={() => connectProvider('linkedin', 'reminder_popup')}>
            Connect LinkedIn
          </button>
          <button class="ghost" type="button" onclick={() => connectProvider('microsoft', 'reminder_popup')}>
            Connect Microsoft
          </button>
          <button class="ghost subtle" type="button" onclick={() => (showReminder = false)}>Maybe later</button>
        </div>
      </section>
    </div>
  {/if}
</AppShell>

<style>
  .settings-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.2fr) minmax(320px, 420px);
    gap: 1rem;
  }

  .settings-column,
  .profile-card,
  .summary-card,
  .workspace-card {
    display: grid;
    gap: 1rem;
    align-content: start;
  }

  .profile-card,
  .summary-card,
  .workspace-card {
    padding: 1.2rem;
  }

  .profile-hero {
    display: grid;
    grid-template-columns: 64px 1fr;
    gap: 0.9rem;
    align-items: center;
  }

  .avatar {
    width: 64px;
    height: 64px;
    border-radius: 18px;
    display: grid;
    place-items: center;
    background: var(--gradient-brand);
    color: #fff;
    font-weight: 700;
    box-shadow: var(--shadow-glow-blue);
  }

  h2,
  h3 {
    margin: 0;
  }

  .field-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.9rem;
  }

  label {
    display: grid;
    gap: 0.45rem;
  }

  input {
    border-radius: 14px;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.03);
    color: var(--ink);
    padding: 0.9rem 1rem;
  }

  .panel-strip {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8rem;
  }

  .data-point,
  .cardlet {
    border: 1px solid var(--line);
    border-radius: 18px;
    background: rgba(255,255,255,0.03);
    padding: 1rem;
  }

  .data-point strong,
  .provider-card strong {
    display: block;
  }

  .data-point span,
  .scope-note,
  .detail {
    color: var(--muted);
    font-size: 0.9rem;
  }

  .provider-card {
    border: 1px solid var(--line);
    border-radius: 18px;
    background: rgba(255,255,255,0.03);
    padding: 1rem;
    display: grid;
    gap: 0.8rem;
  }

  .provider-topline {
    display: flex;
    justify-content: space-between;
    gap: 0.8rem;
    align-items: start;
    flex-wrap: wrap;
  }

  .status {
    border-radius: 999px;
    padding: 0.45rem 0.75rem;
    border: 1px solid var(--line);
    background: rgba(255,255,255,0.04);
    text-transform: capitalize;
    color: var(--ink-soft);
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
    min-height: 50px;
    border-radius: 16px;
    border: 1px solid var(--line);
    background: transparent;
    color: var(--ink-strong);
    padding: 0.85rem 1rem;
  }

  .link-card {
    display: grid;
    place-items: center;
  }

  .feedback {
    border-radius: 16px;
    padding: 0.95rem 1rem;
    border: 1px solid rgba(255,255,255,0.08);
  }

  .feedback.error {
    color: #fecaca;
    background: rgba(127, 29, 29, 0.28);
    border-color: rgba(239, 68, 68, 0.22);
  }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(5, 8, 12, 0.56);
    display: grid;
    place-items: center;
    padding: 1.5rem;
    z-index: 30;
  }

  .reminder-modal {
    width: min(520px, 100%);
    padding: 1.35rem;
    display: grid;
    gap: 0.95rem;
    box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
  }

  .modal-actions {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .subtle {
    color: var(--muted);
  }

  @media (max-width: 980px) {
    .settings-grid {
      grid-template-columns: 1fr;
    }

    .field-grid,
    .panel-strip {
      grid-template-columns: 1fr;
    }
  }
</style>
