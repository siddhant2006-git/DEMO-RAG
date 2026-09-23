from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import SessionLocal

router = APIRouter()


@router.get("/health")
def health() -> dict:
    db_status = "up"
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - health check must never raise
        db_status = f"down: {exc.__class__.__name__}"

    return {
        "status": "ok",
        "service": "tenderguard-api",
        "dependencies": {"database": db_status},
    }
