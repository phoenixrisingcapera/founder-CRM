# Railway Deploy

Deploy this repo to Railway as two services from the same GitHub repository.

## Services

1. `founder-crm-api`
   Root directory: `api`

2. `founder-crm-web`
   Root directory: `web`

## API Service

Start is defined in `api/nixpacks.toml`:

```bash
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set these Railway variables:

```bash
CRM_APP_ENV=production
CRM_DATABASE_URL=<railway postgres url>
CRM_AUTH_SECRET_KEY=<strong secret>
CRM_CORS_ORIGINS=<web service url>
CRM_EXPORTS_ENABLED=false
CRM_UPLOADS_ROOT=./storage/uploads
```

Optional:

```bash
CRM_OPENAI_API_KEY=
CRM_OPENAI_MODEL=gpt-4o-mini
CRM_OPENROUTER_API_KEY=
CRM_OPENROUTER_MODEL=openai/gpt-4o-mini
CRM_ENCRYPTION_KEY=
```

## Web Service

Build and start are defined in `web/nixpacks.toml`.

Set these Railway variables:

```bash
PUBLIC_APP_NAME=AiStack Founder CRM
PUBLIC_API_BASE_URL=<api service url>/api
PUBLIC_ENABLE_DEMO_BOOTSTRAP=false
```

## Notes

- `web/` uses `@sveltejs/adapter-node` for Railway.
- `api/` runs Alembic migrations on boot before starting Uvicorn.
- Create a Railway Postgres service and connect its URL to `CRM_DATABASE_URL`.
