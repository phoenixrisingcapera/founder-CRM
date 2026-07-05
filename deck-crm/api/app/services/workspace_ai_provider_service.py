from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.ai.anthropic_provider import call_anthropic_message, extract_anthropic_text
from app.ai.openai_provider import call_openai_response, extract_openai_text
from app.ai.openrouter_provider import call_openrouter_chat_completion, extract_openrouter_text
from app.core.config import settings
from app.core.security import generate_id
from app.core.workspace_ai_crypto import get_workspace_ai_fernet
from app.db.models import Workspace, WorkspaceAiCredential, WorkspaceAiProviderSetting
from app.schemas.workspace_ai_provider import (
    SaveWorkspaceAiProviderRequest,
    WorkspaceAiProviderSummary,
)

MODEL_OPTIONS: dict[str, set[str]] = {
    "openai": {"gpt-5", "gpt-4.1"},
    "openrouter": {"openai/gpt-4o", "openai/gpt-4.1-mini", "openai/gpt-4", "anthropic/claude-sonnet-4.5"},
    "claude": {"claude-sonnet-4-5", "claude-opus-4-1"},
}


def _validate_claude_connection(api_key: str, model: str) -> None:
    response = call_anthropic_message(
        api_key=api_key,
        model=model,
        system="You are validating whether a Claude API key is connected.",
        user="Reply with OK if the key works.",
        max_tokens=1,
        timeout=20,
    )
    extract_anthropic_text(response)


def _validate_openai_connection(api_key: str, model: str) -> None:
    response = call_openai_response(
        api_key=api_key,
        model=model,
        system="You are validating whether an OpenAI API key is connected.",
        user="Reply with OK if the key works.",
        max_output_tokens=8,
        timeout=20,
    )
    extract_openai_text(response)


def _validate_openrouter_connection(api_key: str, model: str) -> None:
    response = call_openrouter_chat_completion(
        api_key=api_key,
        model=model,
        system="You are validating whether an OpenRouter API key is connected.",
        user="Reply with OK if the key works.",
        max_tokens=8,
        timeout=20,
    )
    extract_openrouter_text(response)


def _build_summary(setting: WorkspaceAiProviderSetting | None, credential: WorkspaceAiCredential | None = None) -> WorkspaceAiProviderSummary:
    if setting is None:
        return WorkspaceAiProviderSummary(
            provider=None,
            preferred_model=None,
            api_key_last4=None,
            key_version=None,
            is_configured=False,
            configured_at=None,
            skipped_at=None,
        )

    active_credential = credential
    if active_credential is None and setting.credential_id:
        active_credential = setting.credential  # type: ignore[attr-defined]

    return WorkspaceAiProviderSummary(
        provider=setting.provider,  # type: ignore[arg-type]
        preferred_model=setting.preferred_model,
        api_key_last4=active_credential.api_key_last4 if active_credential else None,
        key_version=active_credential.key_version if active_credential else None,
        is_configured=bool(setting.configured_at and active_credential and active_credential.is_active),
        configured_at=setting.configured_at,
        skipped_at=setting.skipped_at,
    )


def _resolve_workspace(db: Session, user_id: str) -> Workspace:
    workspace = db.query(Workspace).filter(Workspace.user_id == user_id).order_by(Workspace.created_at.asc()).first()
    if workspace is None:
        raise ValueError("Workspace not found")
    return workspace


def get_workspace_ai_provider_summary(db: Session, user_id: str) -> WorkspaceAiProviderSummary:
    workspace = _resolve_workspace(db, user_id)
    setting = (
        db.query(WorkspaceAiProviderSetting)
        .filter(WorkspaceAiProviderSetting.workspace_id == workspace.id)
        .first()
    )

    credential = None
    if setting and setting.credential_id:
        credential = db.query(WorkspaceAiCredential).filter(WorkspaceAiCredential.id == setting.credential_id).first()

    return _build_summary(setting, credential)


def save_workspace_ai_provider(db: Session, user_id: str, payload: SaveWorkspaceAiProviderRequest) -> dict:
    workspace = _resolve_workspace(db, user_id)
    setting = (
        db.query(WorkspaceAiProviderSetting)
        .filter(WorkspaceAiProviderSetting.workspace_id == workspace.id)
        .first()
    )

    if payload.skipForNow:
        if setting is None:
            setting = WorkspaceAiProviderSetting(
                id=generate_id("wais"),
                workspace_id=workspace.id,
                provider=payload.provider,
                preferred_model=payload.preferredModel,
                skipped_at=datetime.utcnow(),
            )
            db.add(setting)
        else:
            setting.provider = payload.provider
            setting.preferred_model = payload.preferredModel
            setting.skipped_at = datetime.utcnow()
        db.commit()
        db.refresh(setting)
        return {
            "summary": _build_summary(setting),
            "next_url": "/welcome",
        }

    if not payload.apiKey.strip():
        raise ValueError("API key is required")

    if (
        payload.preferredModel
        and payload.provider != "openrouter"
        and payload.preferredModel not in MODEL_OPTIONS[payload.provider]
    ):
        raise ValueError("Preferred model is invalid for the selected provider")

    if payload.provider == "claude":
        try:
            _validate_claude_connection(payload.apiKey.strip(), payload.preferredModel or "claude-sonnet-4-5")
        except ValueError as exc:
            raise ValueError(f"Could not connect to Claude with the provided API key: {exc}") from exc
    elif payload.provider == "openai":
        try:
            _validate_openai_connection(payload.apiKey.strip(), payload.preferredModel or "gpt-5")
        except ValueError as exc:
            raise ValueError(f"Could not connect to OpenAI with the provided API key: {exc}") from exc
    elif payload.provider == "openrouter":
        try:
            _validate_openrouter_connection(payload.apiKey.strip(), payload.preferredModel or "openai/gpt-4o")
        except ValueError as exc:
            raise ValueError(f"Could not connect to OpenRouter with the provided API key: {exc}") from exc

    (
        db.query(WorkspaceAiCredential)
        .filter(
            WorkspaceAiCredential.workspace_id == workspace.id,
            WorkspaceAiCredential.provider == payload.provider,
            WorkspaceAiCredential.is_active.is_(True),
        )
        .update(
            {
                WorkspaceAiCredential.is_active: False,
                WorkspaceAiCredential.revoked_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )
    )

    encrypted_key = get_workspace_ai_fernet().encrypt(payload.apiKey.encode())
    credential = WorkspaceAiCredential(
        id=generate_id("waic"),
        workspace_id=workspace.id,
        provider=payload.provider,
        encrypted_api_key=encrypted_key,
        api_key_last4=payload.apiKey[-4:],
        key_version=settings.workspace_ai_fernet_key_version,
        created_by_user_id=user_id,
        is_active=True,
    )
    db.add(credential)
    db.flush()

    if setting is None:
        setting = WorkspaceAiProviderSetting(
            id=generate_id("wais"),
            workspace_id=workspace.id,
            provider=payload.provider,
            preferred_model=payload.preferredModel,
            credential_id=credential.id,
            configured_at=datetime.utcnow(),
            skipped_at=None,
        )
        db.add(setting)
    else:
        setting.provider = payload.provider
        setting.preferred_model = payload.preferredModel
        setting.credential_id = credential.id
        setting.configured_at = datetime.utcnow()
        setting.skipped_at = None

    db.commit()
    db.refresh(setting)
    return {
        "summary": _build_summary(setting, credential),
        "next_url": "/welcome",
    }


def revoke_workspace_ai_provider(db: Session, user_id: str) -> dict:
    workspace = _resolve_workspace(db, user_id)
    setting = (
        db.query(WorkspaceAiProviderSetting)
        .filter(WorkspaceAiProviderSetting.workspace_id == workspace.id)
        .first()
    )
    if setting is None or not setting.credential_id:
        return {
            "summary": _build_summary(setting),
            "revoked": False,
        }

    credential = (
        db.query(WorkspaceAiCredential)
        .filter(
            WorkspaceAiCredential.id == setting.credential_id,
            WorkspaceAiCredential.workspace_id == workspace.id,
        )
        .first()
    )
    if credential is None or not credential.is_active:
        setting.credential_id = None
        setting.configured_at = None
        db.commit()
        db.refresh(setting)
        return {
            "summary": _build_summary(setting),
            "revoked": False,
        }

    credential.is_active = False
    credential.revoked_at = datetime.utcnow()
    setting.credential_id = None
    setting.configured_at = None
    db.commit()
    db.refresh(setting)
    return {
        "summary": _build_summary(setting),
        "revoked": True,
    }
