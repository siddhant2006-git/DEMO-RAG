from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import audit, bids, compliance, health, reports, tenders, verification
from app.config import get_settings
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
app.include_router(tenders.router, prefix="/api/v1")
app.include_router(bids.router, prefix="/api/v1")
app.include_router(verification.router, prefix="/api/v1")
app.include_router(compliance.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("startup", environment=settings.environment, verification_mode=settings.verification_mode)
