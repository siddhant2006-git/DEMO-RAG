import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class VerificationResult(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "verification_results"

    bid_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bids.id", ondelete="CASCADE"), index=True
    )

    portal: Mapped[str] = mapped_column(String(32))  # GST | UDYAM | PAN | MCA | EPFO
    # UP (verified, value present) | DOWN (portal unreachable) | NOT_FOUND
    status: Mapped[str] = mapped_column(String(32))

    normalized: Mapped[dict] = mapped_column(JSON, default=dict)  # adapter's normalized fact dict
    raw_response: Mapped[dict] = mapped_column(JSON, default=dict)

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    bid: Mapped["Bid"] = relationship()
