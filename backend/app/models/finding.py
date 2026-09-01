import uuid

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Finding(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "findings"

    bid_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bids.id", ondelete="CASCADE"), index=True
    )
    requirement_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE"), index=True
    )

    rule_id: Mapped[str] = mapped_column(String(64))  # e.g. REQ-TURNOVER, from the rule pack
    weight: Mapped[float] = mapped_column(Float, default=0.0)

    expected: Mapped[dict] = mapped_column(JSON, default=dict)
    claimed: Mapped[dict] = mapped_column(JSON, default=dict)
    verified: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(16))  # PASS | FAIL | NEEDS_REVIEW
    reason: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16))  # BLOCKER | CRITICAL | MAJOR | MINOR
    risk_contribution: Mapped[float] = mapped_column(Float, default=0.0)

    evidence: Mapped["Evidence | None"] = relationship(
        back_populates="finding", cascade="all, delete-orphan", uselist=False
    )
    requirement = relationship("Requirement")


class Evidence(Base, UUIDPKMixin, TimestampMixin):
    """1:1 with a Finding — enforces that no finding is saved without a source reference."""

    __tablename__ = "evidence"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("findings.id", ondelete="CASCADE"), unique=True, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id"))
    page_number: Mapped[int] = mapped_column(Integer)
    bbox: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [x0, y0, x1, y1]
    snippet: Mapped[str] = mapped_column(Text)
    document_sha256: Mapped[str] = mapped_column(String(64))

    finding: Mapped["Finding"] = relationship(back_populates="evidence")
