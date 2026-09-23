import uuid

from pydantic import BaseModel


class DocumentPageOut(BaseModel):
    page_number: int
    char_count: int
    ocr_used: bool
    ocr_confidence: float | None
    low_confidence: bool
    text_preview: str

    model_config = {"from_attributes": True}


class DocumentOut(BaseModel):
    id: uuid.UUID
    kind: str
    filename: str
    sha256: str
    page_count: int
    status: str

    model_config = {"from_attributes": True}
