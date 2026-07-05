<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData, ActionData } from './$types';
  import type { AdminUser } from '$lib/types/admin';

  let { data, form }: { data: PageData; form?: ActionData } = $props();

  const users = $derived(data.testerUsers as AdminUser[]);

  const pendingApprovals = $derived(
    users
      .filter((user) => user.role === 'general')
      .sort((a, b) => {
        const aTime = Date.parse((a.updatedAt ?? a.updated_at ?? '') || '0');
        const bTime = Date.parse((b.updatedAt ?? b.updated_at ?? '') || '0');
        return bTime - aTime;
      })
  );

  const activeTesters = $derived(
    users
      .filter((user) => user.role === 'user')
      .sort((a, b) => {
        const aTime = Date.parse((a.updatedAt ?? a.updated_at ?? '') || '0');
        const bTime = Date.parse((b.updatedAt ?? b.updated_at ?? '') || '0');
        return bTime - aTime;
      })
  );

  function formatDate(value: string | null | undefined) {
    if (!value) return 'n/a';
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(value));
  }

  function userId(user: { id: string }) {
    return encodeURIComponent(user.id);
  }

  function formatRole(role: string) {
    return role.replaceAll('_', ' ');
  }
</script>

<AppShell
  title="Tester approvals"
  subtitle="Grant and revoke tester access for sign-up users."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="tester-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/failure-tickets">Failure tickets</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/users">Users</a>
      <a class="active" href="/admin/testers">Testers</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
      <a href="/admin/deployment-readiness">Deployment readiness</a>
    </nav>

    <section class="summary-grid" aria-label="Tester status summary">
      <article class="panel summary-card">
        <span>Pending approvals</span>
        <strong>{pendingApprovals.length}</strong>
        <small>Users waiting for tester role</small>
      </article>

      <article class="panel summary-card">
        <span>Active testers</span>
        <strong>{activeTesters.length}</strong>
        <small>Users allowed to access testing</small>
      </article>
    </section>

    <article class="panel table-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Pending tester requests</p>
          <h2>Approve or revoke tester access</h2>
        </div>
      </div>

      {#if form?.message}
        <p class="form-message" role="alert">{form.message}</p>
      {/if}

      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Signed up</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {#each pendingApprovals as user}
              <tr>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td><span class="role-pill">{formatRole(user.role)}</span></td>
                <td>{formatDate(user.createdAt ?? user.created_at ?? null)}</td>
                <td>
                  <form method="POST" action="?/setTesterRole">
                    <input type="hidden" name="userId" value={userId(user)} />
                    <input type="hidden" name="role" value="user" />
                    <button class="button secondary" type="submit">Grant tester access</button>
                  </form>
                </td>
              </tr>
            {/each}
            {#if pendingApprovals.length === 0}
              <tr>
                <td colspan="5" class="empty">No pending tester requests.</td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
    </article>

    <article class="panel table-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Active testers</p>
          <h2>Users currently granted testing access</h2>
        </div>
      </div>

      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Updated</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {#each activeTesters as user}
              <tr>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td><span class="role-pill role-pill--positive">{formatRole(user.role)}</span></td>
                <td>{formatDate(user.updatedAt ?? user.updated_at ?? null)}</td>
                <td>
                  <form method="POST" action="?/setTesterRole">
                    <input type="hidden" name="userId" value={userId(user)} />
                    <input type="hidden" name="role" value="general" />
                    <button class="button secondary" type="submit">Revoke tester access</button>
                  </form>
                </td>
              </tr>
            {/each}
            {#if activeTesters.length === 0}
              <tr>
                <td colspan="5" class="empty">No active testers right now.</td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
    </article>
  </section>
</AppShell>

<style>
  .tester-page {
    display: grid;
    gap: 1rem;
  }

  .admin-tabs {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .admin-tabs a {
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.55rem 0.75rem;
    color: var(--text-muted);
    text-decoration: none;
    background: var(--surface-subtle);
  }

  .admin-tabs a.active {
    color: var(--text);
    border-color: var(--accent);
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    gap: 0.75rem;
  }

  .summary-card,
  .table-panel {
    padding: 1rem;
  }

  .summary-card {
    display: grid;
    gap: 0.35rem;
  }

  .summary-card span,
  .summary-card small {
    color: var(--text-muted);
  }

  .summary-card strong {
    font-size: 1.6rem;
  }

  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    min-width: 820px;
  }

  th,
  td {
    padding: 0.75rem;
    border-bottom: 1px solid var(--border);
    text-align: left;
    vertical-align: top;
  }

  .role-pill {
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.15rem 0.5rem;
    font-size: 0.78rem;
    color: var(--text-muted);
  }

  .role-pill--positive {
    border-color: rgba(34, 197, 94, 0.45);
    color: #86efac;
  }

  .form-message {
    color: #ef4444;
    margin: 0 0 0.8rem;
  }

  .empty {
    color: var(--text-muted);
  }

  @media (max-width: 860px) {
    .table-scroll {
      overflow-x: auto;
    }
  }
</style>
