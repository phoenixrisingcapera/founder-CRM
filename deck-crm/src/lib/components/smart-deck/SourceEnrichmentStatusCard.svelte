<script lang="ts">
  type Props = {
    enrichment?: unknown;
    slideCount?: number;
    blockCount?: number;
  };

  let { enrichment = null, slideCount = 0, blockCount = 0 }: Props = $props();

  function normalizeSourceEnrichment(value: unknown) {
    const record = value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
    if (!Object.keys(record).length) return null;

    const firstString = (...values: unknown[]) => {
      for (const candidate of values) {
        if (typeof candidate === 'string' && candidate.trim()) return candidate.trim();
      }
      return undefined;
    };

    const llmStatus = firstString(record.llmStatus, record.llm_status);
    const source =
      firstString(record.source, record.enrichmentSource, record.enrichment_source) ??
      (llmStatus ? 'llm' : 'unknown');
    const badge =
      source === 'llm'
        ? 'Validated labels'
        : source === 'deterministic'
          ? 'Deterministic labels'
          : source === 'disabled'
            ? 'Enrichment disabled'
            : source === 'missing_provider'
              ? 'Provider missing'
              : source === 'invalid_llm_output'
                ? 'Rejected output'
                : source === 'llm_failed'
                  ? 'LLM fallback'
                  : 'Source labels pending';
    const message =
      source === 'llm'
        ? `Validated source labels are attached${firstString(record.provider, record.llmProvider, record.llm_provider) ? ` via ${firstString(record.provider, record.llmProvider, record.llm_provider)}` : ''}.`
        : source === 'deterministic'
          ? 'Deterministic source labels are attached.'
          : source === 'disabled'
            ? 'Source enrichment is disabled; deterministic labels are attached.'
            : source === 'missing_provider'
              ? 'No enrichment provider was available; deterministic labels are attached.'
              : source === 'invalid_llm_output'
                ? 'The enrichment output was rejected; deterministic labels are attached.'
                : source === 'llm_failed'
                  ? 'The enrichment step fell back to deterministic labels.'
                  : 'Source-label readiness has not been reported yet.';

    return {
      source,
      llmStatus,
      provider: firstString(record.provider, record.llmProvider, record.llm_provider),
      model: firstString(record.model, record.llmModel, record.llm_model),
      message,
      badge
    };
  }

  const status = $derived(normalizeSourceEnrichment(enrichment));
</script>

<section class="source-enrichment-card" aria-label="Source enrichment readiness">
  <div>
    <p class="eyebrow">Source enrichment</p>
    <h2>{status?.badge ?? 'Source labels pending'}</h2>
    <p>{status?.message ?? 'Source-label readiness has not been reported yet.'}</p>
  </div>
  <div class="source-enrichment-meta">
    <span>{slideCount} slides</span>
    <span>{blockCount} blocks</span>
    {#if status?.provider}
      <span>{status.provider}</span>
    {/if}
    {#if status?.model}
      <span>{status.model}</span>
    {/if}
  </div>
</section>

<style>
  .source-enrichment-card {
    display: grid;
    gap: 0.75rem;
    margin-bottom: 1rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    background: var(--surface);
  }

  .source-enrichment-card h2,
  .source-enrichment-card p {
    margin: 0;
  }

  .source-enrichment-card p:not(.eyebrow),
  .source-enrichment-meta span {
    color: var(--text-muted);
  }

  .source-enrichment-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .source-enrichment-meta span {
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 0.3rem 0.55rem;
    background: var(--surface-subtle);
    font-size: 0.8rem;
  }
</style>
