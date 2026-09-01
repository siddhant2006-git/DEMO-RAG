import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Tender(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "tenders"

    title: Mapped[str] = mapped_column(String(512))
    reference_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("documents.id"))

    # goods | works | services — selects which rule pack applies
    category: Mapped[str] = mapped_column(String(32), default="goods")

    document = relationship("Document")
    requirements: Mapped[list["Requirement"]] = relationship(
        back_populates="tender", cascade="all, delete-orphan"
    )
