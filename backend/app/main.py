"""FastAPI application. Every route lives under /api so the Next.js proxy forwards paths unchanged."""

from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.api.routes import admin, auth, classes, content, contract, health, learning, teacher
from app.core.config import get_settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.scheduler_enabled:
        from app.jobs import scheduler

        scheduler.start()
    yield
    if settings.scheduler_enabled:
        from app.jobs import scheduler

        scheduler.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AdaptAid API",
        version="0.1.0",
        description="Adaptive teaching-aid recommendation platform (NTCC minor project).",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
        redirect_slashes=False,
        lifespan=lifespan,
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    api = APIRouter(prefix="/api")
    api.include_router(health.router)
    api.include_router(auth.router)
    api.include_router(classes.router)
    api.include_router(content.router)
    api.include_router(learning.router)
    api.include_router(teacher.router)
    api.include_router(admin.router)
    if settings.enable_contract_routes:
        api.include_router(contract.router)
    app.include_router(api)
    return app


app = create_app()
