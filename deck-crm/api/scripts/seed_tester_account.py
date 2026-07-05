#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _env_or_arg(value: str | None, env_name: str, default: str | None = None) -> str | None:
    if value is not None and value.strip():
        return value.strip()
    env_value = os.getenv(env_name)
    if env_value is not None and env_value.strip():
        return env_value.strip()
    return default


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed an idempotent Deck AIStack tester account for Phase 0 smoke testing.",
    )
    parser.add_argument("--email", help="Tester email. Defaults to DECK_TESTER_EMAIL.")
    parser.add_argument("--password", help="Tester password. Defaults to DECK_TESTER_PASSWORD.")
    parser.add_argument("--name", help="Tester display name. Defaults to DECK_TESTER_NAME.")
    parser.add_argument("--company", help="Workspace/company name. Defaults to DECK_TESTER_COMPANY.")
    parser.add_argument(
        "--role",
        choices=["super_admin", "admin", "user", "general"],
        help="Tester role. Defaults to DECK_TESTER_ROLE or user.",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Reset the password when the tester account already exists.",
    )
    parser.add_argument(
        "--allow-production",
        action="store_true",
        help="Required when APP_ENV or Railway marks the backend as production.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    from app.core.config import settings
    from app.core.security import generate_id, hash_password
    from app.db.models import User
    from app.db.session import SessionLocal
    from app.schemas.user import UserCreate
    from app.services.user_service import ensure_role_permissions, ensure_signup_profile, ensure_workspace

    email = _env_or_arg(args.email, "DECK_TESTER_EMAIL")
    password = _env_or_arg(args.password, "DECK_TESTER_PASSWORD")
    name = _env_or_arg(args.name, "DECK_TESTER_NAME", "Deck Tester")
    company = _env_or_arg(args.company, "DECK_TESTER_COMPANY", "Deck AIStack Tester Workspace")
    role = _env_or_arg(args.role, "DECK_TESTER_ROLE", "user")

    if settings.is_production and not args.allow_production:
        raise SystemExit("Refusing to modify production without --allow-production.")
    if not email:
        raise SystemExit("Missing tester email. Pass --email or set DECK_TESTER_EMAIL.")
    if not password:
        raise SystemExit("Missing tester password. Pass --password or set DECK_TESTER_PASSWORD.")
    if len(password) < 8:
        raise SystemExit("Tester password must be at least 8 characters.")
    if role not in {"super_admin", "admin", "user", "general"}:
        raise SystemExit("Tester role must be one of: super_admin, admin, user, general.")

    normalized_email = email.lower()
    payload = UserCreate(
        email=normalized_email,
        password=password,
        name=name or "Deck Tester",
        role=role,  # type: ignore[arg-type]
        companyName=company,
        acceptedTerms=True,
    )

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == normalized_email).first()
        created = user is None

        if user is None:
            user = User(
                id=generate_id("usr"),
                email=payload.email,
                name=payload.name,
                password_hash=hash_password(payload.password),
                role=payload.role,
            )
            db.add(user)
            db.flush()
        else:
            user.name = payload.name
            user.role = payload.role
            if args.reset_password:
                user.password_hash = hash_password(payload.password)
            db.add(user)
            db.flush()

        ensure_role_permissions(db, user, payload.role)
        workspace = ensure_workspace(db, user, workspace_name=payload.company_name)
        ensure_signup_profile(db, user, payload)
        db.commit()
        db.refresh(user)
        db.refresh(workspace)
        seeded = {
            "email": user.email,
            "role": user.role,
            "workspace_name": workspace.name,
            "workspace_id": workspace.id,
        }
    finally:
        db.close()

    action = "created" if created else "updated"
    password_note = "password reset" if not created and args.reset_password else "password unchanged" if not created else "password set"
    print(f"Tester account {action}: {seeded['email']}")
    print(f"Role: {seeded['role']}")
    print(f"Workspace: {seeded['workspace_name']} ({seeded['workspace_id']})")
    print(f"Password state: {password_note}")
    print("Smoke path: /auth/sign-in -> /welcome -> /decks/new -> /decks/{deckId}/smart-deck")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
