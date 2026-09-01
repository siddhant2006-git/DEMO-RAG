import uuid

from pydantic import BaseModel

from app.schemas.document import DocumentOut


class BidUploadOut(BaseModel):
    bid_id: uuid.UUID
    vendor_id: uuid.UUID
    document: DocumentOut
    job_id: str
    duplicate: bool
