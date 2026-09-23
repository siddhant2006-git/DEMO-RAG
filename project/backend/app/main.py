from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.routes import (
    auth,
    audit,
    bids,
    compliance,
    health,
    reports,
    tenders,
    verification,
)
from app.config import PROJECT_ROOT, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging, get_logger

settings = get_settings()
configure_logging(settings.debug)
logger = get_logger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="AI Tender & Vendor Compliance Verification",
    version="0.1.0",
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(auth.router, prefix="/api/v1")
app.include_router(tenders.router, prefix="/api/v1")
app.include_router(bids.router, prefix="/api/v1")
app.include_router(verification.router, prefix="/api/v1")
app.include_router(compliance.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "startup",
        environment=settings.environment,
        verification_mode=settings.verification_mode,
    )


# Serves the built React app (frontend/dist) from the same origin/port as the
# API, so there's one process to run and no CORS/proxy needed. Only mounts
# when a build exists (`npm run build` in frontend/) — an unbuilt frontend
# leaves the API-only app untouched, e.g. under pytest or when using the
# separate Vite dev server instead.
_frontend_dist = PROJECT_ROOT / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=_frontend_dist / "assets"),
        name="frontend-assets",
    )

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str) -> FileResponse:
        candidate = _frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_frontend_dist / "index.html")
