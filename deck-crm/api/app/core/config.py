import base64
import binascii
import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.railway_env import apply_railway_env_aliases


apply_railway_env_aliases()


DEFAULT_AUTH_SECRET = "change-me"
DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/deck_aistack_codes"
DATABASE_URL_ENV_CANDIDATES = (
    "DATABASE_URL",
    "DATABASE_PRIVATE_URL",
    "DATABASE_PUBLIC_URL",
    "POSTGRES_URL",
    "POSTGRES_PRIVATE_URL",
    "POSTGRES_PUBLIC_URL",
    "RAILWAY_DATABASE_URL",
)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _is_valid_fernet_key(value: str) -> bool:
    try:
        decoded = base64.urlsafe_b64decode(value.encode("utf-8"))
    except (binascii.Error, ValueError):
        return False
    return len(decoded) == 32


def _is_placeholder(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    lowered = stripped.lower()
    return (
        stripped.startswith("<")
        and stripped.endswith(">")
    ) or "real railway postgres url" in lowered or "your postgres" in lowered


def _with_postgres_sslmode(url: str) -> str:
    if not url.startswith(("postgresql+psycopg://", "postgresql://", "postgres://")):
        return url
    parts = urlsplit(url)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    if any(key == "sslmode" for key, _value in query_items):
        return url
    query_items.append(("sslmode", "require"))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query_items), parts.fragment))


def _normalize_database_url_scheme(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def _is_parseable_database_url(value: str) -> bool:
    if _is_placeholder(value):
        return False
    candidate = _normalize_database_url_scheme(value.strip())
    if candidate.startswith("sqlite"):
        return True
    if not candidate.startswith(("postgresql+psycopg://", "postgresql://", "postgres://")):
        return False
    parsed = urlsplit(candidate)
    return bool(parsed.scheme and parsed.netloc)


def _resolve_database_url(value: str) -> str:
    """Resolve Railway database aliases and avoid deploying literal placeholders.

    Railway can expose both `DATABASE_URL` and `DATABASE_PUBLIC_URL` / `DATABASE_PRIVATE_URL`.
    During manual configuration it is easy to leave `DATABASE_URL` as a literal
    placeholder such as `<real Railway Postgres URL>`. Alembic then crashes with a
    low-level SQLAlchemy parse error. Resolve a valid Railway URL here before
    settings reach Alembic or the runtime engine.
    """

    candidates: list[tuple[str, str]] = [("DATABASE_URL", value)]
    for env_name in DATABASE_URL_ENV_CANDIDATES:
        env_value = os.getenv(env_name, "")
        if env_value:
            candidates.append((env_name, env_value))

    seen: set[str] = set()
    for _name, candidate in candidates:
        candidate = candidate.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if _is_parseable_database_url(candidate):
            return _normalize_database_url_scheme(candidate)

    return value


class Settings(BaseSettings):
    app_name: str = "Deck AI Stack API"
    app_env: str = "development"
    port: int = 8080
    cors_origin: str = Field(
        default="http://localhost:5173",
        validation_alias=AliasChoices("cors_origin", "CORS_ORIGIN", "FRONTEND_URL"),
    )
    allowed_origins: str = Field(
        default="",
        validation_alias=AliasChoices("allowed_origins", "ALLOWED_ORIGINS", "CORS_ALLOWED_ORIGINS"),
    )
    database_url: str = Field(
        default=DEFAULT_DATABASE_URL,
        validation_alias=AliasChoices(*DATABASE_URL_ENV_CANDIDATES, "database_url"),
    )
    auth_secret_key: str = DEFAULT_AUTH_SECRET
    auth_secret_key_id: str = "local-dev"
    workspace_ai_fernet_key: str = ""
    workspace_ai_fernet_key_version: str = "local-dev"
    auth_token_expiry_minutes: int = 60
    auth_token_issuer: str = "deck-aistack-codes-api"
    auth_token_audience: str = "deck-aistack-codes-web"
    public_signup_enabled: bool = False
    user_admin_bootstrap_token: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-5"
    openai_timeout_seconds: int = 60
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o"
    openrouter_timeout_seconds: int = 60
    openrouter_site_url: str = ""
    openrouter_app_name: str = "Deck AI Stack"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5"
    anthropic_max_tokens: int = 4096
    anthropic_timeout_seconds: int = 60
    anthropic_max_retries: int = 1
    anthropic_retry_delay_seconds: float = 0.25
    superadmin_guardrails_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SUPERADMIN_GUARDRAILS_URL",
            "SUPERADMIN_GUARDRAILS_BASE_URL",
            "AISTACK_GUARDRAILS_URL",
        ),
    )
    superadmin_guardrails_api_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SUPERADMIN_GUARDRAILS_API_KEY",
            "SUPERADMIN_GUARDRAILS_KEY",
            "AISTACK_GUARDRAILS_API_KEY",
        ),
    )
    superadmin_guardrails_timeout_seconds: float = Field(
        default=2.5,
        validation_alias=AliasChoices(
            "SUPERADMIN_GUARDRAILS_TIMEOUT_SECONDS",
            "AISTACK_GUARDRAILS_TIMEOUT_SECONDS",
        ),
    )
    superadmin_guardrails_strict_mode: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "SUPERADMIN_GUARDRAILS_STRICT_MODE",
            "AISTACK_GUARDRAILS_STRICT_MODE",
        ),
    )
    superadmin_aistack_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "SUPERADMIN_AISTACK_URL",
            "SUPERADMIN_AISTACK_BASE_URL",
            "AISTACK_SUPERADMIN_URL",
        ),
    )
    superadmin_aistack_timeout_seconds: float = Field(
        default=2.5,
        validation_alias=AliasChoices(
            "SUPERADMIN_AISTACK_TIMEOUT_SECONDS",
            "AISTACK_SUPERADMIN_TIMEOUT_SECONDS",
        ),
    )
    deck_knowledge_index_path: str = ""
    deck_generation_mode: str = Field(
        default="claude",
        validation_alias=AliasChoices(
            "deck_generation_mode",
            "DECK_GENERATION_MODE",
            "DECK_AISTACK_GENERATION_MODE",
        ),
    )
    upload_storage_backend: str = Field(
        default="local",
        validation_alias=AliasChoices("DECK_AISTACK_STORAGE_PROVIDER", "UPLOAD_STORAGE_BACKEND", "upload_storage_backend"),
    )
    uploads_root: str = "/tmp/deck_aistack_codes_uploads"
    upload_storage_s3_bucket: str = Field(
        default="",
        validation_alias=AliasChoices(
            "upload_storage_s3_bucket",
            "S3_BUCKET_NAME",
            "AWS_S3_BUCKET_NAME",
            "UPLOAD_STORAGE_S3_BUCKET",
            "RAILWAY_BUCKET_NAME",
        ),
    )
    upload_storage_s3_prefix: str = "deck-aistack-codes/uploads"
    upload_storage_s3_region: str = Field(
        default="",
        validation_alias=AliasChoices(
            "upload_storage_s3_region",
            "AWS_DEFAULT_REGION",
            "UPLOAD_STORAGE_S3_REGION",
            "RAILWAY_BUCKET_REGION",
        ),
    )
    upload_storage_s3_endpoint_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AWS_ENDPOINT_URL",
            "UPLOAD_STORAGE_S3_ENDPOINT",
            "RAILWAY_BUCKET_ENDPOINT",
        ),
    )
    deck_aistack_bucket_public: bool = False
    deck_aistack_signed_url_ttl_seconds: int = 900
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = ""
    railway_bucket_access_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AWS_ACCESS_KEY_ID",
            "UPLOAD_STORAGE_S3_ACCESS_KEY",
            "RAILWAY_BUCKET_ACCESS_KEY",
        ),
    )
    railway_bucket_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "AWS_SECRET_ACCESS_KEY",
            "UPLOAD_STORAGE_S3_SECRET_KEY",
            "RAILWAY_BUCKET_SECRET_KEY",
        ),
    )
    aws_access_key_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "aws_access_key_id",
            "AWS_ACCESS_KEY_ID",
            "UPLOAD_STORAGE_S3_ACCESS_KEY",
            "RAILWAY_BUCKET_ACCESS_KEY",
        ),
    )
    aws_secret_access_key: str = Field(
        default="",
        validation_alias=AliasChoices(
            "aws_secret_access_key",
            "AWS_SECRET_ACCESS_KEY",
            "UPLOAD_STORAGE_S3_SECRET_KEY",
            "RAILWAY_BUCKET_SECRET_KEY",
        ),
    )
    max_request_body_size_bytes: int = 210 * 1024 * 1024
    upload_security_scan_command: str = ""
    upload_security_scan_timeout_seconds: int = 30
    turnstile_secret_key: str = ""
    turnstile_verify_timeout_seconds: int = 5
    ai_daily_generation_quota: int = 100
    app_role: str = Field(
        default="api",
        validation_alias=AliasChoices("app_role", "APP_ROLE"),
    )
    railway_environment: str = ""
    otel_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("otel_enabled", "OTEL_ENABLED"),
    )
    otel_service_name: str = Field(
        default="deck-aistack-backend",
        validation_alias=AliasChoices("otel_service_name", "OTEL_SERVICE_NAME"),
    )
    otel_exporter_otlp_endpoint: str = Field(
        default="",
        validation_alias=AliasChoices("otel_exporter_otlp_endpoint", "OTEL_EXPORTER_OTLP_ENDPOINT"),
    )
    otel_exporter_otlp_headers: str = Field(
        default="",
        validation_alias=AliasChoices("otel_exporter_otlp_headers", "OTEL_EXPORTER_OTLP_HEADERS"),
    )
    otel_sample_rate: float = Field(
        default=1.0,
        validation_alias=AliasChoices("otel_sample_rate", "OTEL_SAMPLE_RATE"),
    )

    @field_validator("database_url")
    @classmethod
    def normalize_db_scheme(cls, v: str) -> str:
        return _resolve_database_url(v)

    @model_validator(mode="before")
    @classmethod
    def _prefer_explicit_database_url(cls, values: dict) -> dict:
        if not isinstance(values, dict):
            return values
        if "database_url" in values:
            for candidate in DATABASE_URL_ENV_CANDIDATES:
                if candidate != "database_url":
                    values.pop(candidate, None)
        return values

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production" or self.railway_environment.lower() == "production"

    @property
    def cors_origins(self) -> list[str]:
        return _split_csv(self.allowed_origins or self.cors_origin)

    @property
    def superadmin_guardrails_enabled(self) -> bool:
        return bool(self.superadmin_guardrails_url.strip())

    @property
    def superadmin_aistack_enabled(self) -> bool:
        return bool(self.superadmin_aistack_url.strip())

    def _validate_production_database_url(self, errors: list[str]) -> None:
        if self.database_url == DEFAULT_DATABASE_URL or "localhost" in self.database_url or not _is_parseable_database_url(self.database_url):
            errors.append("DATABASE_URL must point to a valid production database URL or Railway DATABASE_PRIVATE_URL/DATABASE_PUBLIC_URL reference")
        else:
            self.database_url = _with_postgres_sslmode(self.database_url)

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if not self.is_production:
            return self

        runtime_role = self.app_role.strip().lower()
        is_worker = runtime_role == "worker"
        is_migration = runtime_role == "migration"
        errors: list[str] = []

        if is_migration:
            # Alembic/pre-deploy migrations only need a production database URL.
            # Runtime-specific checks still run when APP_ROLE=api or APP_ROLE=worker.
            self._validate_production_database_url(errors)
            if errors:
                raise ValueError("Unsafe production migration settings: " + "; ".join(errors))
            return self

        if self.app_env.lower() != "production":
            errors.append("APP_ENV must be production for production deployments")
        if not is_worker:
            if self.auth_secret_key == DEFAULT_AUTH_SECRET or len(self.auth_secret_key) < 32 or _is_placeholder(self.auth_secret_key):
                errors.append("AUTH_SECRET_KEY must be set to a real non-default value at least 32 characters long")
            if not self.auth_secret_key_id or self.auth_secret_key_id == "local-dev" or _is_placeholder(self.auth_secret_key_id):
                errors.append("AUTH_SECRET_KEY_ID must identify the active production signing key")
            if not self.workspace_ai_fernet_key or _is_placeholder(self.workspace_ai_fernet_key):
                errors.append("WORKSPACE_AI_FERNET_KEY is required in production")
            elif not _is_valid_fernet_key(self.workspace_ai_fernet_key):
                errors.append("WORKSPACE_AI_FERNET_KEY must be a valid Fernet key")
            if (
                not self.workspace_ai_fernet_key_version
                or self.workspace_ai_fernet_key_version == "local-dev"
                or _is_placeholder(self.workspace_ai_fernet_key_version)
            ):
                errors.append("WORKSPACE_AI_FERNET_KEY_VERSION must identify the active production key")
            if self.ai_daily_generation_quota <= 0:
                errors.append("AI_DAILY_GENERATION_QUOTA must be greater than zero in production")
            if self.deck_generation_mode.strip().lower() == "mock":
                errors.append("DECK_GENERATION_MODE=mock is only allowed in local testing")
            if not self.openai_api_key and not self.openrouter_api_key and not self.anthropic_api_key:
                errors.append("At least one production AI provider key is required: OPENAI_API_KEY, OPENROUTER_API_KEY, or ANTHROPIC_API_KEY")
            if self.openai_timeout_seconds <= 0 or self.openai_timeout_seconds > 120:
                errors.append("OPENAI_TIMEOUT_SECONDS must be between 1 and 120 in production")
            if self.openrouter_timeout_seconds <= 0 or self.openrouter_timeout_seconds > 120:
                errors.append("OPENROUTER_TIMEOUT_SECONDS must be between 1 and 120 in production")
            if self.anthropic_timeout_seconds <= 0 or self.anthropic_timeout_seconds > 120:
                errors.append("ANTHROPIC_TIMEOUT_SECONDS must be between 1 and 120 in production")
            if self.anthropic_max_retries < 0 or self.anthropic_max_retries > 3:
                errors.append("ANTHROPIC_MAX_RETRIES must be between 0 and 3 in production")
            if self.anthropic_retry_delay_seconds < 0 or self.anthropic_retry_delay_seconds > 10:
                errors.append("ANTHROPIC_RETRY_DELAY_SECONDS must be between 0 and 10")
            if self.turnstile_verify_timeout_seconds <= 0 or self.turnstile_verify_timeout_seconds > 15:
                errors.append("TURNSTILE_VERIFY_TIMEOUT_SECONDS must be between 1 and 15 in production")
            if self.max_request_body_size_bytes <= 0:
                errors.append("MAX_REQUEST_BODY_SIZE_BYTES must be greater than zero in production")
            if self.app_role == "api" and self.upload_storage_backend == "local" and "upload_storage_backend" in self.__pydantic_fields_set__:
                errors.append("UPLOAD_STORAGE_BACKEND=local is not allowed in production")
            if not self.upload_security_scan_command or _is_placeholder(self.upload_security_scan_command):
                errors.append("upload_security_scan_command is required in production")
            if self.upload_storage_backend == "local":
                if not self.uploads_root.startswith("/"):
                    errors.append("uploads_root must be an absolute path in production")
                if self.uploads_root.startswith("/tmp"):
                    errors.append("uploads_root must not use /tmp in production")
            for origin in self.cors_origins:
                lowered = origin.lower().strip()
                if lowered == "*" or "localhost" in lowered:
                    errors.append("CORS settings must not use wildcard or localhost origins in production")
                    break
            if self.otel_enabled and not self.otel_service_name:
                errors.append("OTEL_SERVICE_NAME is required when OTEL_ENABLED=true")
            if self.otel_sample_rate < 0 or self.otel_sample_rate > 1:
                errors.append("OTEL_SAMPLE_RATE must be between 0 and 1")
        if self.upload_storage_backend not in {"local", "s3", "supabase"}:
            errors.append("UPLOAD_STORAGE_BACKEND must be a supported storage backend")
        if self.upload_storage_backend == "local":
            pass
        if self.upload_storage_backend == "s3":
            s3_access_key = self.railway_bucket_access_key or self.aws_access_key_id
            s3_secret_key = self.railway_bucket_secret_key or self.aws_secret_access_key
            if not self.upload_storage_s3_bucket or _is_placeholder(self.upload_storage_s3_bucket):
                errors.append("S3_BUCKET_NAME, AWS_S3_BUCKET_NAME, UPLOAD_STORAGE_S3_BUCKET, or RAILWAY_BUCKET_NAME is required when UPLOAD_STORAGE_BACKEND=s3")
            if not self.upload_storage_s3_region or _is_placeholder(self.upload_storage_s3_region):
                errors.append("AWS_DEFAULT_REGION, UPLOAD_STORAGE_S3_REGION, or RAILWAY_BUCKET_REGION is required when UPLOAD_STORAGE_BACKEND=s3")
            if not s3_access_key or _is_placeholder(s3_access_key):
                errors.append("AWS_ACCESS_KEY_ID, UPLOAD_STORAGE_S3_ACCESS_KEY, or RAILWAY_BUCKET_ACCESS_KEY is required when UPLOAD_STORAGE_BACKEND=s3")
            if not s3_secret_key or _is_placeholder(s3_secret_key):
                errors.append("AWS_SECRET_ACCESS_KEY, UPLOAD_STORAGE_S3_SECRET_KEY, or RAILWAY_BUCKET_SECRET_KEY is required when UPLOAD_STORAGE_BACKEND=s3")
            endpoint = self.upload_storage_s3_endpoint_url.strip()
            if endpoint and _is_placeholder(endpoint):
                errors.append("AWS_ENDPOINT_URL, UPLOAD_STORAGE_S3_ENDPOINT, or RAILWAY_BUCKET_ENDPOINT must be a real endpoint when provided")
        self._validate_production_database_url(errors)
        if errors:
            raise ValueError("Unsafe production settings: " + "; ".join(errors))
        return self

    model_config = SettingsConfigDict(env_file=str(Path(__file__).resolve().parents[2] / ".env"), env_file_encoding="utf-8", extra="ignore")


settings = Settings()
