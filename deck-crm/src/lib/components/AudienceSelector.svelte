<script lang="ts">
  interface Props {
    value?: string;
  }

  const audiences = [
    'Investment Committee',
    'VC Partner',
    'VC Associate',
    'Strategic Investor',
    'Family Office',
    'LP',
    'Corporate Development',
    'M&A Buyer',
    'Board',
    'Accelerator'
  ];

  // The intake flow binds this field from parent pages, so the prop must stay bindable.
  let { value = $bindable('Investment Committee') }: Props = $props();
</script>

<label class="selector">
  <span>Audience</span>
  <select name="audience" bind:value>
    {#each audiences as audience}
      <option value={audience}>{audience}</option>
    {/each}
  </select>
</label>

<style>
  .selector {
    display: grid;
    gap: 0.45rem;
  }

  select {
    border-radius: var(--radius-sm);
    border: 1px solid var(--line-strong);
    background: rgba(255, 255, 255, 0.82);
    padding: 0.8rem 0.9rem;
  }
</style>
