<script lang="ts">
  import { deckServiceClient } from '$lib/api/deckServiceClient';

  interface Props {
    sourcePage?: string;
  }

  let { sourcePage = 'home' }: Props = $props();

  const roleOptions = [
    'VC / investor',
    'Founder',
    'Advisor',
    'Corporate development',
    'Family office',
    'M&A / investment banking',
    'Other'
  ];

  const useCaseOptions = [
    'Review startup decks',
    'Prepare IC materials',
    'Redesign investor decks',
    'Create strategic investor versions',
    'Create LP / board updates',
    'Explore product',
    'Other'
  ];

  let form = $state({
    email: '',
    name: '',
    company_name: '',
    company_website_url: '',
    role_label: roleOptions[0],
    use_case: useCaseOptions[0],
    message: ''
  });
  let submitting = $state(false);
  let successMessage = $state('');
  let errorMessage = $state('');

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    submitting = true;
    successMessage = '';
    errorMessage = '';

    try {
      const response = await deckServiceClient.submitPublicInterest({
        ...form,
        source_page: sourcePage
      });
      successMessage = response.message;
      form = {
        email: '',
        name: '',
        company_name: '',
        company_website_url: '',
        role_label: roleOptions[0],
        use_case: useCaseOptions[0],
        message: ''
      };
    } catch (error) {
      errorMessage = error instanceof Error ? error.message : 'Unable to record your interest right now.';
    } finally {
      submitting = false;
    }
  }
</script>

<section class="panel section" id="show-interest">
  <div class="section-head">
    <div>
      <div class="eyebrow">Show interest</div>
      <h2>Interested in Deck AIStack?</h2>
      <p class="muted">
        Tell us about yourself and how you plan to use Deck AIStack. Interest submissions are captured as
        general leads and do not automatically create a full app user.
      </p>
    </div>

    <aside class="interest-aside">
      <div class="interest-aside__graphic"></div>
      <p class="muted">We respect your privacy and keep this as a pre-access commercial intake.</p>
    </aside>
  </div>

  <form class="interest-form" onsubmit={handleSubmit}>
    <label>
      <span>Email</span>
      <input bind:value={form.email} type="email" required placeholder="you@fund.com" />
    </label>
    <label>
      <span>Name</span>
      <input bind:value={form.name} placeholder="Andrea Capera" />
    </label>
    <label>
      <span>Company</span>
      <input bind:value={form.company_name} placeholder="Fund or company name" />
    </label>
    <label>
      <span>Company website</span>
      <input bind:value={form.company_website_url} type="url" placeholder="https://company.com" />
    </label>
    <label>
      <span>Role</span>
      <select bind:value={form.role_label}>
        {#each roleOptions as option}
          <option value={option}>{option}</option>
        {/each}
      </select>
    </label>
    <label>
      <span>Use case</span>
      <select bind:value={form.use_case}>
        {#each useCaseOptions as option}
          <option value={option}>{option}</option>
        {/each}
      </select>
    </label>
    <label class="full">
      <span>Message</span>
      <textarea bind:value={form.message} rows="4" placeholder="What do you want to use Deck AIStack for?"></textarea>
    </label>
    <div class="full form-actions">
      <button class="button" type="submit" disabled={submitting}>
        {submitting ? 'Submitting...' : 'Show interest'}
      </button>
      {#if successMessage}
        <p class="success">{successMessage}</p>
      {/if}
      {#if errorMessage}
        <p class="error">{errorMessage}</p>
      {/if}
    </div>
  </form>
</section>

<style>
  .section {
    padding: 1.45rem;
    display: grid;
    gap: 1rem;
  }

  .section-head {
    display: grid;
    grid-template-columns: minmax(0, 1.1fr) 260px;
    gap: 1rem;
    align-items: center;
  }

  .interest-form {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.9rem;
  }

  label {
    display: grid;
    gap: 0.4rem;
  }

  .full {
    grid-column: 1 / -1;
  }

  .interest-aside {
    border: 1px solid var(--line);
    border-radius: var(--radius-card);
    background: var(--surface-soft);
    padding: 1rem;
    display: grid;
    gap: 0.8rem;
  }

  .interest-aside__graphic {
    min-height: 6.5rem;
    border-radius: var(--radius-md);
    background:
      radial-gradient(circle at 30% 30%, var(--glow-blue), transparent 32%),
      radial-gradient(circle at 75% 25%, var(--glow-pink), transparent 28%),
      linear-gradient(135deg, var(--surface-active), var(--surface-soft));
    border: 1px solid var(--line);
  }

  input,
  select,
  textarea {
    border-radius: 14px;
    border: 1px solid var(--line);
    background: var(--surface-input);
    color: var(--ink);
    padding: 0.9rem 1rem;
  }

  .form-actions {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .success {
    margin: 0;
    color: var(--success);
  }

  .error {
    margin: 0;
    color: var(--danger);
  }

  @media (max-width: 1100px) {
    .section-head,
    .interest-form {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }

  @media (max-width: 760px) {
    .section-head,
    .interest-form {
      grid-template-columns: 1fr;
    }
  }
</style>
