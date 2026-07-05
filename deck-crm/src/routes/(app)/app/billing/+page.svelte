<script lang="ts">
  import AppShell from '$components/AppShell.svelte';
  import PageHeader from '$components/PageHeader.svelte';
  import type { PageData } from './$types';

  let { data }: { data: PageData } = $props();

  const currency = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  });

  function formatPrice(value: number | null) {
    return value === null ? 'Custom' : currency.format(value / 100);
  }
</script>

<AppShell
  title="Choose the right plan for your deck workflow"
  subtitle="Workspace billing is served through secure contracts and a server-rendered billing snapshot."
  activeNav="billing"
  deckLabel={data.billing.workspace.name}
>
  <section class="section-stack app-content-narrow">
    <PageHeader
      eyebrow="Billing"
      title="Plan selection and workspace subscription"
      subtitle="Layout aligned to the billing reference while using the global Deck AIStack theme tokens."
      aside={data.billing.subscription
        ? `Current plan: ${data.billing.currentPlan?.name ?? 'None'} • ${data.billing.subscription.interval}`
        : 'No active subscription'}
    />

    <section class="panel billing-panel">
      <div class="plan-grid">
        {#each data.billing.plans as plan}
          <article class:featured={plan.isHighlighted} class="plan-card">
            <div class="eyebrow">{plan.name}</div>
            <div class="plan-copy">
              <h2>
                {formatPrice(plan.monthlyPriceCents)}
                {#if plan.monthlyPriceCents !== null}
                  <span>/month</span>
                {/if}
              </h2>
              <p class="muted">{plan.description}</p>
              {#if plan.seatLabel}
                <p class="seat-label">{plan.seatLabel}</p>
              {/if}
            </div>

            <ul>
              {#each plan.featureBullets as feature}
                <li>{feature}</li>
              {/each}
            </ul>

            <button class:button={plan.isHighlighted} class:ghost={!plan.isHighlighted} type="button">
              {plan.ctaLabel}
            </button>
          </article>
        {/each}
      </div>
    </section>

    <section class="detail-grid">
      <section class="panel subscription-card">
        <div class="eyebrow">Current subscription</div>
        {#if data.billing.subscription && data.billing.currentPlan}
          <div class="subscription-top">
            <div>
              <h3>{data.billing.currentPlan.name}</h3>
              <p class="muted">Status: {data.billing.subscription.status} • Seats: {data.billing.subscription.seatCount}</p>
            </div>
            <div class="pill">{data.billing.subscription.interval}</div>
          </div>
          <dl class="subscription-metrics">
            <div>
              <dt>Current period</dt>
              <dd>{new Date(data.billing.subscription.currentPeriodStart).toLocaleDateString()} - {new Date(data.billing.subscription.currentPeriodEnd).toLocaleDateString()}</dd>
            </div>
            <div>
              <dt>Cancel at period end</dt>
              <dd>{data.billing.subscription.cancelAtPeriodEnd ? 'Yes' : 'No'}</dd>
            </div>
          </dl>
        {:else}
          <p class="muted">No subscription record exists for this workspace yet.</p>
        {/if}
      </section>

      <section class="panel invoice-card">
        <div class="eyebrow">Recent invoices</div>
        <div class="invoice-list">
          {#each data.billing.invoices as invoice}
            <article class="invoice-row">
              <div>
                <strong>{invoice.invoiceNumber}</strong>
                <p class="muted">{new Date(invoice.issuedAt).toLocaleDateString()}</p>
              </div>
              <div class="invoice-right">
                <span class="pill">{invoice.status}</span>
                <strong>{currency.format(invoice.amountCents / 100)}</strong>
              </div>
            </article>
          {/each}
        </div>
      </section>
    </section>
  </section>
</AppShell>

<style>
  .billing-panel,
  .subscription-card,
  .invoice-card {
    padding: 1.2rem;
  }

  .plan-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 1rem;
  }

  .plan-card {
    border: 1px solid var(--line);
    border-radius: 20px;
    padding: 1.35rem;
    background: rgba(255,255,255,0.03);
    display: grid;
    align-content: start;
    gap: 1rem;
  }

  .plan-copy {
    display: grid;
    gap: 0.7rem;
  }

  .plan-card h2 {
    margin: 0;
    font-size: clamp(2rem, 3vw, 3rem);
    letter-spacing: -0.05em;
  }

  .plan-card h2 span {
    font-size: 1.05rem;
    margin-left: 0.3rem;
    color: var(--muted);
  }

  .seat-label {
    margin: 0;
    color: var(--ink-soft);
  }

  ul {
    margin: 0;
    padding-left: 1rem;
    color: var(--ink-soft);
    display: grid;
    gap: 0.65rem;
  }

  .featured {
    box-shadow: var(--shadow), var(--shadow-glow-blue);
    border-color: var(--line-strong);
  }

  .ghost {
    min-height: 50px;
    border-radius: 16px;
    border: 1px solid var(--line);
    background: transparent;
    color: var(--ink-strong);
  }

  .detail-grid {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 420px;
    gap: 1rem;
  }

  .subscription-top,
  .invoice-row,
  .invoice-right {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
  }

  .subscription-metrics {
    margin: 1rem 0 0;
    display: grid;
    gap: 0.9rem;
  }

  .subscription-metrics dt {
    font-size: 0.82rem;
    color: var(--muted);
  }

  .subscription-metrics dd {
    margin: 0.25rem 0 0;
    font-weight: 600;
  }

  .invoice-list {
    display: grid;
    gap: 0.85rem;
  }

  .invoice-row {
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 0.95rem 1rem;
    background: rgba(255,255,255,0.03);
  }

  .invoice-row p {
    margin: 0.25rem 0 0;
  }

  @media (max-width: 1200px) {
    .plan-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .detail-grid {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 720px) {
    .plan-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
