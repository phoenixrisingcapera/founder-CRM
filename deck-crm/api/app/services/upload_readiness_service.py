from __future__ import annotations

from app.core.config import DEFAULT_AUTH_SECRET, DEFAULT_DATABASE_URL, settings


def _configured(value: str | None) -> bool:
    return bool((value or "").strip())


def _not_local_or_default(value: str | None) -> bool:
    candidate = (value or "").strip().lower()
    return bool(candidate) and candidate != DEFAULT_DATABASE_URL.lower() and "localhost" not in candidate


def _check(
    *,
    key: str,
    label: str,
    ok: bool,
    env_names: list[str],
    message: str,
    required: bool = True,
) -> dict:
    return {
        "key": key,
        "label": label,
        "ok": ok,
        "required": required,
        "envNames": env_names,
        "message": message,
    }


def get_upload_persistence_readiness() -> dict:
    """Return a safe, non-secret checklist for diagnosing deck_upload_save 503s.

    This intentionally reports only presence/shape booleans and accepted env names.
    It must not expose secret values, database URLs, bucket credentials, or signed URLs.
    """

    checks = {
        "databaseUrl": _check(
            key="databaseUrl",
            label="Database URL",
            ok=_not_local_or_default(settings.database_url) or not settings.is_production,
            env_names=[
                "DATABASE_URL",
                "DATABASE_PRIVATE_URL",
                "DATABASE_PUBLIC_URL",
                "POSTGRES_URL",
                "POSTGRES_PRIVATE_URL",
                "POSTGRES_PUBLIC_URL",
                "RAILWAY_DATABASE_URL",
            ],
            message="Production uploads require a real Postgres database URL.",
        ),
        "authSecretKey": _check(
            key="authSecretKey",
            label="Auth secret key",
            ok=(settings.auth_secret_key != DEFAULT_AUTH_SECRET and len(settings.auth_secret_key) >= 32) or not settings.is_production,
            env_names=["AUTH_SECRET_KEY"],
            message="Production upload routes require a real auth signing secret.",
        ),
        "authSecretKeyId": _check(
            key="authSecretKeyId",
            label="Auth secret key id",
            ok=(settings.auth_secret_key_id not in {"", "local-dev"}) or not settings.is_production,
            env_names=["AUTH_SECRET_KEY_ID"],
            message="Production upload routes require an active auth signing key id.",
        ),
        "workspaceAiFernetKey": _check(
            key="workspaceAiFernetKey",
            label="Workspace AI Fernet key",
            ok=_configured(settings.workspace_ai_fernet_key) or not settings.is_production,
            env_names=["WORKSPACE_AI_FERNET_KEY"],
            message="Workspace AI provider settings require an encryption key in production.",
        ),
        "workspaceAiFernetKeyVersion": _check(
            key="workspaceAiFernetKeyVersion",
            label="Workspace AI Fernet key version",
            ok=(settings.workspace_ai_fernet_key_version not in {"", "local-dev"}) or not settings.is_production,
            env_names=["WORKSPACE_AI_FERNET_KEY_VERSION"],
            message="Workspace AI provider settings require an active encryption key version in production.",
        ),
        "corsOrigin": _check(
            key="corsOrigin",
            label="CORS origin",
            ok=bool(settings.cors_origins),
            env_names=["ALLOWED_ORIGINS", "CORS_ORIGIN", "CORS_ALLOWED_ORIGINS", "FRONTEND_URL"],
            message="Frontend origin must be allowed so upload/session requests can carry auth cookies.",
        ),
        "uploadSecurityScanCommand": _check(
            key="uploadSecurityScanCommand",
            label="Upload security scan command",
            ok=_configured(settings.upload_security_scan_command),
            env_names=["UPLOAD_SECURITY_SCAN_COMMAND"],
            message="Production persisted uploads should define the malware/security scan command.",
        ),
        "storageBackend": _check(
            key="storageBackend",
            label="Upload storage backend",
            ok=settings.upload_storage_backend in {"s3", "supabase"} or not settings.is_production,
            env_names=["DECK_AISTACK_STORAGE_PROVIDER", "UPLOAD_STORAGE_BACKEND"],
            message="Production uploads must use durable storage, normally s3 on Railway.",
        ),
        "s3Bucket": _check(
            key="s3Bucket",
            label="S3 bucket",
            ok=settings.upload_storage_backend != "s3" or _configured(settings.upload_storage_s3_bucket),
            env_names=["S3_BUCKET_NAME", "AWS_S3_BUCKET_NAME", "UPLOAD_STORAGE_S3_BUCKET", "RAILWAY_BUCKET_NAME"],
            message="S3 uploads require a configured bucket name.",
            required=settings.upload_storage_backend == "s3",
        ),
        "s3Endpoint": _check(
            key="s3Endpoint",
            label="S3 endpoint",
            ok=settings.upload_storage_backend != "s3" or _configured(settings.upload_storage_s3_endpoint_url),
            env_names=["AWS_ENDPOINT_URL", "UPLOAD_STORAGE_S3_ENDPOINT", "RAILWAY_BUCKET_ENDPOINT"],
            message="Railway S3-compatible buckets should expose an endpoint URL.",
            required=settings.upload_storage_backend == "s3",
        ),
        "s3Region": _check(
            key="s3Region",
            label="S3 region",
            ok=settings.upload_storage_backend != "s3" or _configured(settings.upload_storage_s3_region),
            env_names=["AWS_DEFAULT_REGION", "UPLOAD_STORAGE_S3_REGION", "RAILWAY_BUCKET_REGION"],
            message="S3 uploads require a bucket region.",
            required=settings.upload_storage_backend == "s3",
        ),
        "s3AccessKey": _check(
            key="s3AccessKey",
            label="S3 access key",
            ok=settings.upload_storage_backend != "s3" or _configured(settings.railway_bucket_access_key),
            env_names=["AWS_ACCESS_KEY_ID", "UPLOAD_STORAGE_S3_ACCESS_KEY", "RAILWAY_BUCKET_ACCESS_KEY"],
            message="S3 uploads require a bucket access key.",
            required=settings.upload_storage_backend == "s3",
        ),
        "s3SecretKey": _check(
            key="s3SecretKey",
            label="S3 secret key",
            ok=settings.upload_storage_backend != "s3" or _configured(settings.railway_bucket_secret_key),
            env_names=["AWS_SECRET_ACCESS_KEY", "UPLOAD_STORAGE_S3_SECRET_KEY", "RAILWAY_BUCKET_SECRET_KEY"],
            message="S3 uploads require a bucket secret key.",
            required=settings.upload_storage_backend == "s3",
        ),
    }

    required_checks = [check for check in checks.values() if check["required"]]
    missing = [check["key"] for check in required_checks if not check["ok"]]
    warning = [check["key"] for check in checks.values() if not check["required"] and not check["ok"]]
    hard_ok = not missing

    return {
        "ok": hard_ok,
        "status": "ok" if hard_ok and not warning else "warning" if hard_ok else "failed",
        "failureCategory": "deck_upload_save",
        "storageBackend": settings.upload_storage_backend,
        "appEnv": settings.app_env,
        "railwayEnvironment": settings.railway_environment,
        "appRole": settings.app_role,
        "checks": checks,
        "missingRequiredChecks": missing,
        "warningChecks": warning,
        "acceptedVariableGroups": {
            key: check["envNames"] for key, check in checks.items()
        },
    }


def get_upload_failure_diagnostic_summary() -> dict:
    readiness = get_upload_persistence_readiness()
    return {
        "failureCategory": readiness["failureCategory"],
        "status": readiness["status"],
        "storageBackend": readiness["storageBackend"],
        "missingRequiredChecks": readiness["missingRequiredChecks"],
        "warningChecks": readiness["warningChecks"],
        "acceptedVariableGroups": readiness["acceptedVariableGroups"],
    }
