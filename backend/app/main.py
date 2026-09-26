from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1.routes import (
    audit,
    auth,
    bids,
    compliance,
    health,
    reports,
    tenders,
    verification,
)
from app.config import get_settings
from app.core.deps import get_current_user
from app.core.errors import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging, get_logger

settings = get_settings()
configure_logging(settings.debug)
logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response


app = FastAPI(
    title=settings.app_name,
    description="AI Tender & Vendor Compliance Verification",
    version="0.1.0",
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
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
protected = {"dependencies": [Depends(get_current_user)]}
app.include_router(tenders.router, prefix="/api/v1", **protected)
app.include_router(bids.router, prefix="/api/v1", **protected)
app.include_router(verification.router, prefix="/api/v1", **protected)
app.include_router(compliance.router, prefix="/api/v1", **protected)
app.include_router(reports.router, prefix="/api/v1", **protected)
app.include_router(audit.router, prefix="/api/v1", **protected)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info(
        "startup",
        environment=settings.environment,
        verification_mode=settings.verification_mode,
    )
