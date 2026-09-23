import uuid

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Vendor(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "vendors"

    name: Mapped[str] = mapped_column(String(512))
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True, index=True)
    pan: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    udyam_number: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)

    bids: Mapped[list["Bid"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")


class Bid(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "bids"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), index=True
    )
    tender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id"))

    claims_msme_benefit: Mapped[bool] = mapped_column(Boolean, default=False)

    vendor: Mapped["Vendor"] = relationship(back_populates="bids")
    tender = relationship("Tender")
    document = relationship("Document")
    claimed_facts: Mapped[list["ClaimedFact"]] = relationship(
        back_populates="bid", cascade="all, delete-orphan"
    )


class ClaimedFact(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "claimed_facts"

    bid_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("bids.id", ondelete="CASCADE"), index=True
    )

    # dotted fact path matching the rule pack, e.g. "financials.avg_annual_turnover"
    fact_key: Mapped[str] = mapped_column(String(128), index=True)
    raw_value: Mapped[str] = mapped_column(Text)  # verbatim string as extracted
    normalized_value: Mapped[dict] = mapped_column(JSON, default=dict)  # {"value": ..., "unit": ...}

    source_page: Mapped[int] = mapped_column(Integer)
    source_snippet: Mapped[str] = mapped_column(Text)

    bid: Mapped["Bid"] = relationship(back_populates="claimed_facts")
