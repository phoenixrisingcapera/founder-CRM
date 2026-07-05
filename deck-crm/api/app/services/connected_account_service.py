from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import generate_id
from app.db.models import ConnectedAccount, User

PROVIDER_SCOPES = {
    "microsoft": ["User.Read", "Mail.ReadBasic"],
    "linkedin": ["r_liteprofile", "r_emailaddress"],
}


def _serialize_account(account: ConnectedAccount) -> dict:
    return {
        "id": account.id,
        "userId": account.user_id,
        "provider": account.provider,
        "status": account.status,
        "externalAccountId": account.external_account_id,
        "externalEmail": account.external_email,
        "externalDisplayName": account.external_display_name,
        "scopes": account.scopes_json or [],
        "accessTokenMasked": account.access_token_masked,
        "refreshTokenStored": account.refresh_token_stored,
        "externalProfileUrl": account.external_profile_url,
        "lastSyncedAt": account.last_synced_at,
        "syncMetadata": account.sync_metadata_json or {},
        "createdAt": account.created_at,
        "updatedAt": account.updated_at,
    }


def list_connected_accounts(db: Session, user: User) -> list[dict]:
    accounts = (
        db.query(ConnectedAccount)
        .filter(ConnectedAccount.user_id == user.id)
        .order_by(ConnectedAccount.provider.asc(), ConnectedAccount.created_at.asc())
        .all()
    )
    return [_serialize_account(account) for account in accounts]


def connect_account_for_testing(
    db: Session,
    user: User,
    provider: str,
    *,
    origin: str | None = None,
) -> dict:
    account = (
        db.query(ConnectedAccount)
        .filter(ConnectedAccount.user_id == user.id, ConnectedAccount.provider == provider)
        .first()
    )

    if account is None:
        account = ConnectedAccount(
            id=generate_id("connacct"),
            user_id=user.id,
            provider=provider,
        )
        db.add(account)

    account.status = "connected"
    account.external_account_id = account.external_account_id or f"{provider}:{user.id}"
    account.external_email = user.email
    account.external_display_name = user.name
    account.scopes_json = PROVIDER_SCOPES.get(provider, [])
    account.access_token_masked = None
    account.refresh_token_stored = False
    account.external_profile_url = account.external_profile_url
    account.last_synced_at = datetime.now(UTC)
    account.sync_metadata_json = {
        "origin": origin,
        "connectionMode": "tester_persisted",
        "oauthTokensStored": False,
    }

    db.commit()
    db.refresh(account)
    return _serialize_account(account)
