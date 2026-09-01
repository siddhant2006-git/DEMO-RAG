import uuid

from pydantic import BaseModel

from app.schemas.document import DocumentOut


class TenderUploadOut(BaseModel):
    tender_id: uuid.UUID
    document: DocumentOut
    job_id: str
    duplicate: bool
