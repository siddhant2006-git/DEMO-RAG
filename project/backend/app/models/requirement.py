import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Requirement(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "requirements"

    tender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), index=True
    )

    external_ref: Mapped[str | None] = mapped_column(String(32), nullable=True)  # e.g. REQ-014
    text: Mapped[str] = mapped_column(Text)

    # fixed taxonomy bucket: turnover | experience | certification | registration
    # | financial | technical | msme | debarment | manual_review
    category: Mapped[str] = mapped_column(String(64), default="manual_review")

    # {"operator": "gte", "value": 50000000, "unit": "INR"}
    expected: Mapped[dict] = mapped_column(JSON, default=dict)

    source_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id"), nullable=True
    )
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)

    human_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tender: Mapped["Tender"] = relationship(back_populates="requirements")
