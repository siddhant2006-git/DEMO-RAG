import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import AppError
from app.models.document import Document, DocumentKind
from app.services.ingestion.hashing import sha256_file

settings = get_settings()


@dataclass
class SavedUpload:
    document: Document
    duplicate: bool


def validate_pdf_upload(filename: str, content_type: str | None, size_bytes: int) -> None:
    if not filename.lower().endswith(".pdf") and content_type != "application/pdf":
        raise AppError("INVALID_FILE_TYPE", "Only PDF files are accepted", 400)

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size_bytes > max_bytes:
        raise AppError(
            "FILE_TOO_LARGE",
            f"File exceeds the {settings.max_upload_mb}MB limit",
            400,
            {"max_upload_mb": settings.max_upload_mb, "received_bytes": size_bytes},
        )
    if size_bytes == 0:
        raise AppError("EMPTY_FILE", "Uploaded file is empty", 400)


def save_upload(db: Session, *, kind: DocumentKind, filename: str, content: bytes) -> SavedUpload:
    """Writes the file to disk, hashes it, and reuses an existing Document row
    with the same hash instead of storing (and re-ingesting) a duplicate.

    Looked up by hash alone, not (hash, kind): `documents.sha256` is globally
    unique at the DB level, so the same bytes uploaded once as a tender and
    again as a bid must resolve to the one existing row (whichever kind it
    was first stored as) — filtering by kind here would miss that row and
    then hit the unique constraint on insert.
    """
    kind_dir = Path(settings.upload_dir) / kind.value.lower()
    kind_dir.mkdir(parents=True, exist_ok=True)

    tmp_path = kind_dir / f"{uuid.uuid4()}.pdf"
    tmp_path.write_bytes(content)
    file_hash = sha256_file(str(tmp_path))

    existing = db.execute(select(Document).where(Document.sha256 == file_hash)).scalar_one_or_none()

    if existing is not None:
        tmp_path.unlink(missing_ok=True)
        return SavedUpload(document=existing, duplicate=True)

    document = Document(
        kind=kind,
        filename=filename,
        storage_path=str(tmp_path),
        sha256=file_hash,
        status="pending",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return SavedUpload(document=document, duplicate=False)
