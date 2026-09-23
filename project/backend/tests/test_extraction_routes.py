import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401 - registers all tables on Base.metadata
from app.core.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.document import Document, DocumentKind
from app.models.tender import Tender
from app.schemas.extraction import ExtractedRequirement
from app.services.extraction import enqueue as extraction_enqueue
from app.services.extraction.tender_requirements import GroundedRequirement


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A route-level (not-quite-full-stack) test: a real temp sqlite file
    behind the app's normal get_db dependency, the LLM boundary stubbed out
    so the test doesn't need Ollama running, and Redis treated as
    unreachable so extraction runs inline synchronously."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(extraction_enqueue, "is_redis_reachable", lambda: False)
    # The inline extraction path (see services/extraction/enqueue.py) opens
    # its own session via app.db.session.SessionLocal rather than FastAPI's
    # get_db — same pattern ingestion's inline path uses, since a worker
    # can't share a request's dependency-injected session. Point that at
    # the same temp engine so the request and the inline extraction it
    # triggers see the same data.
    monkeypatch.setattr("app.db.session.SessionLocal", TestSessionLocal)

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_extract_then_review_flow(client, monkeypatch):
    """A1 + A2 end to end: extraction persists a page-cited requirement
    bound to its rule (external_ref set), and an officer can then PATCH it
    to confirm review — recorded with reviewer identity and timestamp."""
    def fake_extract_requirements_from_document(client_, pages):
        return [
            GroundedRequirement(
                page_number=2,
                requirement=ExtractedRequirement(
                    text="Bidder must have average annual turnover >= 5 Cr in last 3 FY.",
                    category="turnover",
                    expected_operator="gte",
                    expected_value=50_000_000,
                    expected_unit="INR",
                    source_snippet="turnover >= 5 Cr",
                ),
            )
        ]

    monkeypatch.setattr(
        "app.services.extraction.tender_requirements.extract_requirements_from_document",
        fake_extract_requirements_from_document,
    )
    monkeypatch.setattr("app.services.llm.client.OllamaClient.__init__", lambda self: None)
    monkeypatch.setattr("app.services.llm.client.OllamaClient.close", lambda self: None)

    # Seed the tender + document directly through the overridden session —
    # upload would need a real PDF for PyMuPDF ingestion, which is
    # orthogonal to what this test is checking (extraction + review).
    from app.core.deps import get_db as get_db_dep

    gen = app.dependency_overrides[get_db_dep]()
    db = next(gen)
    try:
        doc = Document(
            kind=DocumentKind.TENDER, filename="t.pdf", storage_path="t.pdf", sha256="tsha", status="done"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        tender = Tender(title="Sample Tender", category="goods", document_id=doc.id)
        db.add(tender)
        db.commit()
        db.refresh(tender)
        tender_id = str(tender.id)
    finally:
        db.close()

    resp = client.post(f"/api/v1/tenders/{tender_id}/extract")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "done"
    assert body["requirements_created"] == 1

    resp = client.get(f"/api/v1/tenders/{tender_id}/requirements")
    assert resp.status_code == 200
    reqs = resp.json()
    assert len(reqs) == 1
    req = reqs[0]
    assert req["external_ref"] == "REQ-TURNOVER"
    assert req["source_page"] == 2
    assert req["human_reviewed"] is False

    resp = client.patch(
        f"/api/v1/tenders/{tender_id}/requirements/{req['id']}",
        json={"human_reviewed": True},
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["human_reviewed"] is True
    assert updated["reviewed_by"] == "officer"
    assert updated["reviewed_at"] is not None


def test_extract_requires_ingestion_done(client):
    from app.core.deps import get_db as get_db_dep

    gen = app.dependency_overrides[get_db_dep]()
    db = next(gen)
    try:
        doc = Document(
            kind=DocumentKind.TENDER, filename="t.pdf", storage_path="t.pdf", sha256="tsha2", status="pending"
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        tender = Tender(title="Sample Tender", category="goods", document_id=doc.id)
        db.add(tender)
        db.commit()
        db.refresh(tender)
        tender_id = str(tender.id)
    finally:
        db.close()

    resp = client.post(f"/api/v1/tenders/{tender_id}/extract")
    assert resp.status_code == 409
