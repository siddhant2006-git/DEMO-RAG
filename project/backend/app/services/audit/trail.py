from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    """Appends one audit log row. Never updates or deletes an existing row —
    that's what makes the trail trustworthy."""
    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
