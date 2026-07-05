from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.db.models import User
from app.schemas.deployment_readiness import DeploymentReadinessResponse
from app.services.railway_upload_smoke_test_service import run_railway_upload_smoke_test
from app.services.deployment_readiness_service import get_deployment_readiness

router = APIRouter(prefix="/admin", tags=["deployment-readiness"])


@router.get(
    "/deployment-readiness",
    response_model=DeploymentReadinessResponse,
    dependencies=[Depends(require_roles("super_admin"))],
)
def admin_deployment_readiness(db: Session = Depends(get_db)) -> DeploymentReadinessResponse:
    return DeploymentReadinessResponse(**get_deployment_readiness(db))


@router.post(
    "/railway-upload-smoke-test",
    dependencies=[Depends(require_roles("super_admin"))],
)
async def admin_railway_upload_smoke_test(
    cleanup: bool = Query(default=True, description="Set to false to keep the test deck in workspace."),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return await run_railway_upload_smoke_test(db, current_user, cleanup=cleanup)
