FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        clamav \
        libreoffice \
        poppler-utils \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# Railway service settings can override railway.toml and still run
# `alembic upgrade head` as a pre-deploy command. Suppress that CLI call on
# Railway only; runtime migrations still run via `python -m alembic` from
# scripts/start_railway.py.
RUN if [ -x /usr/local/bin/alembic ]; then mv /usr/local/bin/alembic /usr/local/bin/alembic.real; fi \
    && printf '%s\n' \
        '#!/bin/sh' \
        'if [ "$1" = "upgrade" ] && [ "$2" = "head" ] && { [ -n "${RAILWAY_ENVIRONMENT:-}" ] || [ -n "${RAILWAY_ENVIRONMENT_ID:-}" ] || [ -n "${RAILWAY_SERVICE_NAME:-}" ] || [ -n "${RAILWAY_PROJECT_ID:-}" ]; }; then' \
        '  echo "Railway pre-deploy alembic CLI suppressed; migrations run from scripts/start_railway.py."' \
        '  exit 0' \
        'fi' \
        'exec python -m alembic "$@"' \
        > /usr/local/bin/alembic \
    && chmod +x /usr/local/bin/alembic

COPY . ./

RUN python llm_knowledge/deck_archetype_knowledge/scripts/compile_deck_archetypes.py \
    --src llm_knowledge/deck_archetype_knowledge/source_md \
    --out llm_knowledge/deck_archetype_knowledge/compiled_json

CMD ["python", "scripts/start_railway.py"]
