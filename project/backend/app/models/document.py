import uuid
from enum import Enum as PyEnum

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class DocumentKind(str, PyEnum):
    TENDER = "TENDER"
    BID = "BID"


class Document(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "documents"

    kind: Mapped[DocumentKind] = mapped_column(Enum(DocumentKind, name="document_kind"))
    filename: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    page_count: Mapped[int] = mapped_column(Integer, default=0)

    # ingestion job status: pending | processing | done | failed
    status: Mapped[str] = mapped_column(String(32), default="pending")

    pages: Mapped[list["DocumentPage"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", order_by="DocumentPage.page_number"
    )


class DocumentPage(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "document_pages"

    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    page_number: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, default="")

    # true when the embedded text layer was too sparse and OCR was used instead
    ocr_used: Mapped[bool] = mapped_column(default=False)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_confidence: Mapped[bool] = mapped_column(default=False)

    # per-line/word bounding boxes kept for evidence highlighting:
    # [{"text": "...", "bbox": [x0, y0, x1, y1]}, ...]
    layout: Mapped[list] = mapped_column(JSON, default=list)

    document: Mapped["Document"] = relationship(back_populates="pages")
