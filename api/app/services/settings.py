from sqlalchemy.orm import Session

from app.core.security import decrypt_secret, encrypt_secret
from app.db.models import User, UserApiKey


def save_user_api_key(db: Session, user: User, provider: str, api_key: str) -> UserApiKey:
    record = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user.id, UserApiKey.provider == provider)
        .one_or_none()
    )
    if record is None:
        record = UserApiKey(user_id=user.id, provider=provider, encrypted_api_key=encrypt_secret(api_key))
        db.add(record)
    else:
        record.encrypted_api_key = encrypt_secret(api_key)
    db.commit()
    db.refresh(record)
    return record


def list_user_api_key_summaries(db: Session, user: User) -> list[dict[str, bool | str]]:
    records = db.query(UserApiKey).filter(UserApiKey.user_id == user.id).all()
    return [{"provider": item.provider, "configured": True} for item in records]


def resolve_user_api_key(db: Session, user: User, provider: str | None = None) -> tuple[str | None, str | None]:
    query = db.query(UserApiKey).filter(UserApiKey.user_id == user.id)
    if provider:
        query = query.filter(UserApiKey.provider == provider)
        record = query.one_or_none()
        return (record.provider, decrypt_secret(record.encrypted_api_key)) if record else (None, None)

    record = query.order_by(UserApiKey.created_at.desc()).first()
    return (record.provider, decrypt_secret(record.encrypted_api_key)) if record else (None, None)
