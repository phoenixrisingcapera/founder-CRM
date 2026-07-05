from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.schemas.billing import (
    BillingInvoiceListRouteResponse,
    BillingPlanListRouteResponse,
    WorkspaceSubscriptionUpdateRequest,
    WorkspaceSubscriptionRouteResponse,
)
from app.services.billing_service import get_workspace_subscription, list_billing_invoices, list_billing_plans, switch_workspace_subscription

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=BillingPlanListRouteResponse)
def billing_plans(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingPlanListRouteResponse:
    return BillingPlanListRouteResponse(plans=list_billing_plans(db))


@router.get("/subscription", response_model=WorkspaceSubscriptionRouteResponse)
def billing_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceSubscriptionRouteResponse:
    return WorkspaceSubscriptionRouteResponse(subscription=get_workspace_subscription(db, current_user))


@router.post("/subscription", response_model=WorkspaceSubscriptionRouteResponse)
def billing_subscription_update(
    payload: WorkspaceSubscriptionUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkspaceSubscriptionRouteResponse:
    try:
        subscription = switch_workspace_subscription(db, current_user, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if subscription is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceSubscriptionRouteResponse(subscription=subscription)


@router.get("/invoices", response_model=BillingInvoiceListRouteResponse)
def billing_invoices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BillingInvoiceListRouteResponse:
    return BillingInvoiceListRouteResponse(invoices=list_billing_invoices(db, current_user))
