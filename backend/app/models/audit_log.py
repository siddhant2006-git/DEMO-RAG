from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import UUIDPKMixin


class AuditLog(Base, UUIDPKMixin):
    """Append-only — never updated or deleted, only inserted."""

    __tablename__ = "audit_logs"

    actor: Mapped[str] = mapped_column(String(256))
    action: Mapped[str] = mapped_column(String(128))  # e.g. tender.upload, requirement.edit
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))

    before: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
