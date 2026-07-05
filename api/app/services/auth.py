from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import AudienceProfile, FounderWorkspace, User


DEMO_EMAIL = "founder@aistack.local"

DEFAULT_AUDIENCES = [
    ("angel", "Angel", "Concise traction and founder-market-fit framing for angel conversations."),
    ("seed-vc", "Seed VC", "Seed narrative focused on market pull, repeatability, and early go-to-market signals."),
    ("series-a-vc", "Series A VC", "Growth narrative with operating leverage, category timing, and expansion proof."),
    ("accelerator", "Accelerator", "Program-focused story with coachability, urgency, and founder velocity."),
    ("strategic", "Strategic Investor", "Partnership and ecosystem angle for strategic corporate capital."),
]


def seed_default_audiences(db: Session, workspace: FounderWorkspace) -> None:
    existing_codes = {
        code for (code,) in db.query(AudienceProfile.code).filter(AudienceProfile.workspace_id == workspace.id).all()
    }
    for code, label, description in DEFAULT_AUDIENCES:
        if code in existing_codes:
            continue
        db.add(
            AudienceProfile(
                workspace_id=workspace.id,
                code=code,
                label=label,
                description=description,
            )
        )


def ensure_demo_workspace(db: Session) -> tuple[User, FounderWorkspace]:
    user = db.query(User).filter(User.email == DEMO_EMAIL).one_or_none()
    if user is None:
        user = User(email=DEMO_EMAIL, full_name="AiStack Founder", password_hash=hash_password("change-me-now"))
        db.add(user)
        db.flush()

    workspace = db.query(FounderWorkspace).filter(FounderWorkspace.user_id == user.id).one_or_none()
    if workspace is None:
        workspace = FounderWorkspace(
            user_id=user.id,
            name="AiStack Founder CRM",
            slug="aistack-founder-crm",
            active_raise_name="Seed extension",
        )
        db.add(workspace)
        db.flush()

    seed_default_audiences(db, workspace)
    db.commit()
    db.refresh(user)
    db.refresh(workspace)
    return user, workspace
