<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import EmptyState from '$components/EmptyState.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();
</script>

<AppShell
  title="Team"
  subtitle="Invite collaborators when the workspace is ready for shared review, but keep it optional during first-time onboarding."
  activeNav="team"
  deckLabel={data.workspace.workspace.name}
>
  <EmptyState
    eyebrow="Team collaboration"
    title="Team access is optional"
    message="Invite teammates once the first deck is uploaded and the workspace needs shared review, Smart Edit, or export handoff."
    primaryHref={data.workspace.deckCount === 0 ? '/welcome' : '/settings/account/connected-accounts'}
    primaryLabel={data.workspace.deckCount === 0 ? 'Upload first deck' : 'Manage connected accounts'}
    secondaryHref="/settings"
    secondaryLabel="Open settings"
  />
</AppShell>
