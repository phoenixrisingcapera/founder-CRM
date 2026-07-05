<script lang="ts">
  interface Props {
    filename?: string;
  }

  let { filename = '' }: Props = $props();
</script>

<label class="panel dropzone">
  <input type="file" accept=".pdf,.ppt,.pptx" name="deckFile" />
  <strong>Upload existing PDF or PowerPoint deck</strong>
  <span class="muted">Deck is the source of truth. We parse slides, blocks, and classifications server-side.</span>
  <span class="selected">{filename || 'No file selected yet'}</span>
</label>

<style>
  .dropzone {
    display: grid;
    gap: 0.75rem;
    padding: 1.25rem;
    border-style: dashed;
  }

  input {
    display: block;
  }

  .selected {
    font-size: 0.9rem;
    color: var(--accent);
  }
</style>
