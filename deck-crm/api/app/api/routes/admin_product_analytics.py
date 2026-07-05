from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.services.product_analytics_service import get_product_analytics_metrics

router = APIRouter(prefix="/admin/analytics", tags=["admin-product-analytics"])


@router.get("/model-building-metrics", dependencies=[Depends(require_roles("super_admin"))])
def admin_model_building_metrics(db: Session = Depends(get_db)) -> dict:
    """Export/product analytics for auditing future model-training readiness."""

    return get_product_analytics_metrics(db)
