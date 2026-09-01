from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def list_audit_log(
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Append-only audit trail — every upload, verification run, compliance
    run, and report download. Optionally filtered to one entity, e.g. a
    single bid's full history."""
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.filter(AuditLog.entity_id == entity_id)

    rows = query.order_by(AuditLog.timestamp.desc()).limit(min(limit, 500)).all()
    return [
        {
            "id": str(r.id),
            "actor": r.actor,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "before": r.before,
            "after": r.after,
            "timestamp": r.timestamp.isoformat(),
        }
        for r in rows
    ]
