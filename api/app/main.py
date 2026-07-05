from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.auth import router as auth_router
from app.api.routes.contacts import router as contacts_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.decks import router as decks_router
from app.api.routes.investors import router as investors_router
from app.api.routes.people import router as people_router
from app.api.routes.pipeline import router as pipeline_router
from app.api.routes.settings import router as settings_router
from app.api.routes.venture import router as venture_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.observability import observe_request

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(contacts_router, prefix="/api")
app.include_router(investors_router, prefix="/api")
app.include_router(people_router, prefix="/api")
app.include_router(decks_router, prefix="/api")
app.include_router(pipeline_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(venture_router, prefix="/api")
app.include_router(admin_router, prefix="/api")


@app.middleware("http")
async def telemetry_middleware(request, call_next):
    return await observe_request(request, call_next, SessionLocal)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AiStack Founder CRM API"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aistack-founder-crm-api"}
