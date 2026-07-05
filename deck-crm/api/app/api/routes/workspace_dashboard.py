from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.services.workspace_dashboard_service import get_workspace_dashboard

router = APIRouter(prefix="/workspace", tags=["workspace-dashboard"])


@router.get("/dashboard")
def workspace_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return get_workspace_dashboard(db, current_user)
