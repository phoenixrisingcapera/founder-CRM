<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import type { PageData, ActionData } from './$types';

  let { data, form }: { data: PageData; form?: ActionData } = $props();

  const roleOptions: Array<'super_admin' | 'admin' | 'user' | 'general'> = ['super_admin', 'admin', 'user', 'general'];
  const users = $derived(data.users);
  const roleCounts = $derived(
    roleOptions.reduce<Record<string, number>>((acc, role) => {
      acc[role] = users.filter((item) => item.role === role).length;
      return acc;
    }, {})
  );

  function roleLabel(role: string) {
    return role.replaceAll('_', ' ');
  }

  function formatDate(value: string | null) {
    if (!value) return 'n/a';
    return new Intl.DateTimeFormat('en', {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    }).format(new Date(value));
  }

  function userCreatedAt(user: { createdAt: string | null; created_at?: string | null }) {
    return formatDate(user.createdAt ?? user.created_at ?? null);
  }

  function userUpdatedAt(user: { updatedAt: string | null; updated_at?: string | null }) {
    return formatDate(user.updatedAt ?? user.updated_at ?? null);
  }
</script>

<AppShell
  title="Admin users"
  subtitle="Promote and manage user access roles. All actions are tracked in audit."
  activeNav="admin"
  deckLabel="Admin console"
>
  <section class="users-page">
    <nav class="admin-tabs" aria-label="Admin sections">
      <a href="/admin">Overview</a>
      <a href="/admin/agents">Agent runs</a>
      <a href="/admin/agent-teams">Agent teams</a>
      <a href="/admin/learning">Learning</a>
      <a href="/admin/telemetry">Telemetry</a>
      <a href="/admin/elements">Elements</a>
      <a href="/admin/audit">Audit</a>
      <a href="/admin/failure-tickets">Failure tickets</a>
      <a href="/admin/safety-controls">Safety controls</a>
      <a href="/admin/testers">Testers</a>
      <a class="active" href="/admin/users">Users</a>
      <a href="/admin/quotas">Quotas</a>
      <a href="/admin/provider-health">Provider health</a>
    </nav>

    <section class="summary-grid" aria-label="User role summary">
      {#each roleOptions as role}
        <article class="panel summary-card">
          <span>{roleLabel(role)} users</span>
          <strong>{roleCounts[role] ?? 0}</strong>
          <small>Access control entries</small>
        </article>
      {/each}
    </section>

    <article class="panel table-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">User access</p>
          <h2>{users.length} users in scope</h2>
        </div>
      </div>

      {#if form?.message}
        <p class="form-message" role="alert">{form.message}</p>
      {/if}

      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Created</th>
              <th>Updated</th>
              <th>Assign role</th>
            </tr>
          </thead>
          <tbody>
            {#each users as user}
              <tr>
                <td>{user.name}</td>
                <td>{user.email}</td>
                <td><span class="role-pill">{roleLabel(user.role)}</span></td>
                <td>{userCreatedAt(user)}</td>
                <td>{userUpdatedAt(user)}</td>
                <td>
                  <form class="inline-form" method="POST" action="?/updateRole">
                    <input type="hidden" name="userId" value={user.id} />
                    <select name="role" value={user.role}>
                      {#each roleOptions as role}
                        <option value={role}>{roleLabel(role)}</option>
                      {/each}
                    </select>
                    <button class="button secondary" type="submit">Save</button>
                  </form>
                </td>
              </tr>
            {:else}
              <tr>
                <td colspan="6" class="empty">No users were returned by the admin service.</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </article>
  </section>
</AppShell>

<style>
  .users-page {
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
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
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
    font-size: 1.5rem;
  }

  .table-scroll {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    min-width: 860px;
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
    padding: 0.25rem 0.5rem;
    color: var(--text-muted);
    font-size: 0.78rem;
  }

  .inline-form {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    flex-wrap: nowrap;
  }

  .inline-form select,
  .inline-form button {
    min-width: 0;
  }

  .form-message {
    color: #ef4444;
    margin: 0 0 0.8rem;
  }

  @media (max-width: 860px) {
    .table-scroll {
      overflow-x: auto;
    }
  }
</style>
