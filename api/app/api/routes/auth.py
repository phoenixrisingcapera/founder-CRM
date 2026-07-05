from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_workspace, get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import FounderWorkspace, Project, User
from app.schemas.auth import SignInRequest, SignUpRequest, SessionResponse, SessionUserResponse, SessionWorkspaceResponse
from app.services.auth import ensure_demo_workspace, seed_default_audiences

router = APIRouter(prefix="/auth", tags=["auth"])


def _workspace_response(workspace: FounderWorkspace, db: Session) -> SessionWorkspaceResponse:
    active_project_title = None
    active_goal_type = None
    if workspace.active_project_id:
        proj = db.query(Project).filter(Project.id == workspace.active_project_id).first()
        if proj:
            active_project_title = proj.title
            active_goal_type = proj.goal_type
    return SessionWorkspaceResponse(
        id=workspace.id,
        name=workspace.name,
        slug=workspace.slug,
        active_raise_name=workspace.active_raise_name,
        active_project_id=workspace.active_project_id,
        active_project_title=active_project_title,
        active_goal_type=active_goal_type,
    )


@router.post("/demo-session", response_model=SessionResponse)
def create_demo_session(response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    user, workspace = ensure_demo_workspace(db)
    token = create_access_token(user.id, workspace.id)
    response.set_cookie("crm_session", token, httponly=True, samesite="lax", secure=False, max_age=604800)
    return SessionResponse(
        user=SessionUserResponse(id=user.id, email=user.email, full_name=user.full_name),
        workspace=_workspace_response(workspace, db),
    )


@router.post("/signup", response_model=SessionResponse)
def sign_up(payload: SignUpRequest, response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    existing = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

    user = User(email=payload.email.lower(), full_name=payload.full_name, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    slug_base = payload.email.split("@")[0].lower()
    workspace = FounderWorkspace(user_id=user.id, name=f"{payload.full_name} Workspace", slug=f"{slug_base}-{user.id[:8]}")
    db.add(workspace)
    db.flush()
    seed_default_audiences(db, workspace)
    db.commit()
    db.refresh(user)
    db.refresh(workspace)

    token = create_access_token(user.id, workspace.id)
    response.set_cookie("crm_session", token, httponly=True, samesite="lax", secure=False, max_age=604800)
    return SessionResponse(
        user=SessionUserResponse(id=user.id, email=user.email, full_name=user.full_name),
        workspace=_workspace_response(workspace, db),
    )


@router.post("/login", response_model=SessionResponse)
def login(payload: SignInRequest, response: Response, db: Session = Depends(get_db)) -> SessionResponse:
    user = db.query(User).filter(User.email == payload.email.lower()).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    workspace = db.query(FounderWorkspace).filter(FounderWorkspace.user_id == user.id).one()
    token = create_access_token(user.id, workspace.id)
    response.set_cookie("crm_session", token, httponly=True, samesite="lax", secure=False, max_age=604800)
    return SessionResponse(
        user=SessionUserResponse(id=user.id, email=user.email, full_name=user.full_name),
        workspace=_workspace_response(workspace, db),
    )


@router.post("/logout")
def logout(response: Response) -> dict[str, str]:
    response.delete_cookie("crm_session")
    return {"status": "ok"}


@router.get("/me", response_model=SessionResponse)
def get_session(
    user=Depends(get_current_user),
    workspace=Depends(get_current_workspace),
    db: Session = Depends(get_db),
) -> SessionResponse:
    return SessionResponse(
        user=SessionUserResponse(id=user.id, email=user.email, full_name=user.full_name),
        workspace=_workspace_response(workspace, db),
    )
