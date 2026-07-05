# Backend LLM Knowledge Mount

Place all backend-readable LLM knowledge inside this folder.

Current package:

```text
llm_knowledge/deck_archetype_knowledge
```

The backend should load `compiled_json/archetypes.index.json` as the first knowledge file for deck intelligence.

Recommended environment variables:

```bash
LLM_PROVIDER=your_provider
LLM_MODEL=your_model
DECK_KNOWLEDGE_INDEX_PATH=/app/backend/llm_knowledge/deck_archetype_knowledge/compiled_json/archetypes.index.json
LLM_JSON_STRICT=true
LLM_MAX_RETRIES=2
```
