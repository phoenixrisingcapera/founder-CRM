from __future__ import annotations

from cryptography.fernet import InvalidToken
from sqlalchemy.orm import Session

from app.ai_orchestration.providers import BaseLlmProvider
from app.ai_orchestration.providers.anthropic_provider import AnthropicLlmProvider
from app.ai_orchestration.providers.openai_provider import OpenAiLlmProvider
from app.core.config import settings
from app.core.workspace_ai_crypto import get_workspace_ai_fernet
from app.db.models import Deck, WorkspaceAiCredential, WorkspaceAiProviderSetting


def resolve_orchestration_provider(
    db: Session,
    deck: Deck,
    *,
    preferred_model: str | None = None,
) -> BaseLlmProvider:
    mode = (settings.deck_generation_mode or "").strip().lower()
    if mode == "mock":
        raise ValueError("Mock AI orchestration has moved to the Deck local_testing harness.")

    workspace_provider = _resolve_workspace_provider(db, deck, preferred_model=preferred_model)
    if workspace_provider is not None:
        return workspace_provider

    provider_name = (
        "openai" if mode == "openai" else "claude" if mode in {"claude", "anthropic"} else ""
    )
    if provider_name == "openai" and settings.openai_api_key:
        return OpenAiLlmProvider(
            api_key=settings.openai_api_key,
            model=preferred_model or settings.openai_model,
        )
    if provider_name == "claude" and settings.anthropic_api_key:
        return AnthropicLlmProvider(
            api_key=settings.anthropic_api_key,
            model=preferred_model or settings.anthropic_model,
        )

    if settings.openai_api_key:
        return OpenAiLlmProvider(
            api_key=settings.openai_api_key,
            model=preferred_model or settings.openai_model,
        )
    if settings.anthropic_api_key:
        return AnthropicLlmProvider(
            api_key=settings.anthropic_api_key,
            model=preferred_model or settings.anthropic_model,
        )

    raise ValueError(
        "No AI provider is configured. Add a workspace provider key or set "
        "OPENAI_API_KEY/ANTHROPIC_API_KEY."
    )


def _resolve_workspace_provider(
    db: Session,
    deck: Deck,
    *,
    preferred_model: str | None = None,
) -> BaseLlmProvider | None:
    setting = (
        db.query(WorkspaceAiProviderSetting)
        .filter(
            WorkspaceAiProviderSetting.workspace_id == deck.workspace_id,
            WorkspaceAiProviderSetting.use_for_smart_deck.is_(True),
            WorkspaceAiProviderSetting.configured_at.is_not(None),
        )
        .first()
    )
    if setting is None or not setting.credential_id:
        return None

    credential = (
        db.query(WorkspaceAiCredential)
        .filter(
            WorkspaceAiCredential.id == setting.credential_id,
            WorkspaceAiCredential.workspace_id == deck.workspace_id,
            WorkspaceAiCredential.provider == setting.provider,
            WorkspaceAiCredential.is_active.is_(True),
        )
        .first()
    )
    api_key = _decrypt_workspace_api_key(credential)
    if not api_key:
        return None

    model = preferred_model or setting.preferred_model
    if setting.provider == "openai":
        return OpenAiLlmProvider(api_key=api_key, model=model or settings.openai_model)
    if setting.provider == "claude":
        return AnthropicLlmProvider(api_key=api_key, model=model or settings.anthropic_model)
    return None


def _decrypt_workspace_api_key(credential: WorkspaceAiCredential | None) -> str | None:
    if credential is None or not credential.is_active:
        return None
    try:
        return get_workspace_ai_fernet().decrypt(credential.encrypted_api_key).decode()
    except (InvalidToken, ValueError):
        return None
