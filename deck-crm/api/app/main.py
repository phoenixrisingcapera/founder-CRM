import logging
import time

from app.api.routes.account import router as account_router
from app.ai_orchestration.router import router as ai_orchestration_router
from app.core.security import generate_id
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.assistant import router as assistant_router
from app.api.routes.billing import router as billing_router
from app.api.routes.admin_operations import router as admin_operations_router
from app.api.routes.admin_product_analytics import router as admin_product_analytics_router
from app.api.routes.admin_users import router as admin_users_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.auth import router as auth_router
from app.api.routes.brand_extraction import router as brand_extraction_router
from app.api.routes.blocks import router as blocks_router
from app.api.routes.deck_artifacts import router as deck_artifacts_router
from app.api.routes.deck_intake import router as deck_intake_router
from app.api.routes.deck_retry_rescue import router as deck_retry_rescue_router
from app.api.routes.deck_workflow import router as deck_workflow_router
from app.api.routes.decks import router as decks_router
from app.api.routes.deck_generation import router as deck_generation_router
from app.api.routes.deployment_readiness import router as deployment_readiness_router
from app.api.routes.exports import router as exports_router
from app.api.routes.failure_tickets import router as failure_tickets_router
from app.api.routes.health import router as health_router
from app.api.routes.llm_knowledge_admin import router as llm_knowledge_admin_router
from app.api.routes.product_analytics import router as product_analytics_router
from app.api.routes.product_intake_cleanup import router as product_intake_cleanup_router
from app.api.routes.product_runtime_hardening import router as product_runtime_hardening_router
from app.api.routes.product_upload_compat import router as product_upload_compat_router
from app.api.routes.public_interest import router as public_interest_router
from app.api.routes.products import router as products_router
from app.api.routes.shell import router as shell_router
from app.api.routes.slides import router as slides_router
from app.api.routes.smart_deck import router as smart_deck_router
from app.api.routes.smart_edit import router as smart_edit_router
from app.api.routes.suggestions import router as suggestions_router
from app.api.routes.upload_rescue import router as upload_rescue_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.workspace_ai_provider import router as workspace_ai_provider_router
from app.api.routes.workspace_dashboard import router as workspace_dashboard_router
from app.api.deps import require_resource_access
from app.core.config import settings
from app.db.session import SessionLocal
from app.observability import instrument_fastapi_app
from app.services.failure_ticket_service import create_failure_ticket_from_exception

request_logger = logging.getLogger("app.request")

app = FastAPI(title=settings.app_name)
instrument_fastapi_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type", "X-Requested-With", "X-Request-ID"],
)

app.include_router(health_router, prefix="/api")
app.include_router(account_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(billing_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(public_interest_router, prefix="/api")
# Register rescue, runtime hardening, and compatibility product routes before the broader product router.
app.include_router(upload_rescue_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(product_upload_compat_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(deck_retry_rescue_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(deck_artifacts_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(product_intake_cleanup_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(product_runtime_hardening_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(products_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(ai_orchestration_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(deck_intake_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(deck_workflow_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(shell_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(brand_extraction_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(deck_generation_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(auth_router, prefix="/api")
app.include_router(failure_tickets_router, prefix="/api")
app.include_router(admin_operations_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(admin_product_analytics_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(deployment_readiness_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(admin_users_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(llm_knowledge_admin_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(decks_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(uploads_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(slides_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(smart_deck_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(smart_deck_router, prefix="/api/products/deck-aistack-codes", dependencies=[Depends(require_resource_access)])
app.include_router(blocks_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(analysis_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(assistant_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(suggestions_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(smart_edit_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(exports_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(exports_router, prefix="/api/products/deck-aistack-codes", dependencies=[Depends(require_resource_access)])
app.include_router(product_analytics_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(product_analytics_router, prefix="/api/products/deck-aistack-codes", dependencies=[Depends(require_resource_access)])
app.include_router(workspace_ai_provider_router, prefix="/api", dependencies=[Depends(require_resource_access)])
app.include_router(workspace_dashboard_router, prefix="/api", dependencies=[Depends(require_resource_access)])


@app.middleware("http")
async def add_security_headers(request, call_next):
    started_at = time.perf_counter()
    incoming_request_id = request.headers.get("x-request-id", "").strip()
    request_id = incoming_request_id[:128] if incoming_request_id else generate_id("req")
    request.state.request_id = request_id
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > settings.max_request_body_size_bytes:
        response = JSONResponse({"detail": "Request body is too large"}, status_code=413)
        response = _apply_security_headers(request, response, request_id)
        _log_request(request, response.status_code, request_id, started_at)
        return response

    try:
        response = await call_next(request)
    except Exception as exc:
        _record_unhandled_exception_ticket(request, exc)
        _log_request(request, 500, request_id, started_at, level=logging.ERROR)
        raise
    response = _apply_security_headers(request, response, request_id)
    _log_request(request, response.status_code, request_id, started_at)
    return response


def _log_request(request, status_code: int, request_id: str, started_at: float, *, level: int = logging.INFO) -> None:
    duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
    client_host = request.client.host if request.client is not None else None
    request_logger.log(
        level,
        "http_request",
        extra={
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "client_host": client_host,
        },
    )


def _apply_security_headers(request, response, request_id):
    response.headers.setdefault("X-Request-ID", request_id)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'; base-uri 'none'")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if settings.is_production:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


def _record_unhandled_exception_ticket(request, exc: BaseException) -> None:
    if request.url.path == "/api/admin/failure-tickets/report":
        return
    db = SessionLocal()
    try:
        create_failure_ticket_from_exception(db, request=request, exc=exc, commit=True)
    except Exception:
        request_logger.exception("failure_ticket_record_failed")
        db.rollback()
    finally:
        db.close()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Deck AI Stack FastAPI backend"}


@app.get("/health", tags=["health"])
def root_health() -> dict[str, str]:
    return {"status": "ok", "service": "deck-aistack-codes-backend"}
