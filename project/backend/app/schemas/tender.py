import uuid

from pydantic import BaseModel

from app.schemas.document import DocumentOut
from app.schemas.extraction import REQUIREMENT_CATEGORIES


class TenderUploadOut(BaseModel):
    tender_id: uuid.UUID
    document: DocumentOut
    job_id: str
    duplicate: bool


class TenderExtractOut(BaseModel):
    job_id: str
    status: str  # queued | done
    requirements_created: int | None


class RequirementUpdate(BaseModel):
    """PATCH body for an officer editing an extracted requirement. Every
    field is optional so a request can confirm review (human_reviewed=True)
    without also having to resend text/category/expected unchanged."""

    text: str | None = None
    category: REQUIREMENT_CATEGORIES | None = None
    expected: dict | None = None
    human_reviewed: bool | None = None
