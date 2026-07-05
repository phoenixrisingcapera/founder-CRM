from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from uuid import uuid4

from cryptography.fernet import Fernet
import jwt

from app.core.config import settings


def generate_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


def create_access_token(user_id: str, workspace_id: str) -> str:
    payload = {
        "sub": user_id,
        "workspace_id": workspace_id,
        "purpose": "auth",
        "exp": utcnow() + timedelta(days=7),
    }
    return jwt.encode(payload, settings.auth_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.auth_secret_key, algorithms=["HS256"])
    if payload.get("purpose") != "auth":
        raise ValueError("Invalid token purpose")
    return payload


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 600000)
    return f"{salt}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    salt, stored = password_hash.split("$", 1)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 600000)
    return hmac.compare_digest(derived.hex(), stored)


def create_signed_artifact_token(artifact_id: str) -> str:
    return jwt.encode(
        {
            "artifact_id": artifact_id,
            "purpose": "artifact_download",
            "exp": utcnow() + timedelta(minutes=15),
        },
        settings.auth_secret_key,
        algorithm="HS256",
    )


def decode_signed_artifact_token(token: str) -> dict:
    payload = jwt.decode(token, settings.auth_secret_key, algorithms=["HS256"])
    if payload.get("purpose") != "artifact_download":
        raise ValueError("Invalid token purpose")
    return payload


def encrypt_secret(value: str) -> str:
    if not settings.encryption_key:
        raise ValueError("CRM_ENCRYPTION_KEY is required for persisted API key storage")
    return Fernet(settings.encryption_key.encode("utf-8")).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    if not settings.encryption_key:
        raise ValueError("CRM_ENCRYPTION_KEY is required for persisted API key storage")
    return Fernet(settings.encryption_key.encode("utf-8")).decrypt(value.encode("utf-8")).decode("utf-8")
