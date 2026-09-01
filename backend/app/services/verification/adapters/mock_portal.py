import json
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.services.verification.base import PortalAdapter, VerificationOutcome

settings = get_settings()


@lru_cache
def _load(filename: str) -> dict:
    path = Path(settings.mock_portal_dir) / filename
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class MockGstAdapter(PortalAdapter):
    portal_name = "GST"

    def verify(self, gstin: str = "", **_: str) -> VerificationOutcome:
        record = _load("gst.json").get(gstin)
        if record is None:
            return VerificationOutcome(portal=self.portal_name, status="NOT_FOUND")

        return VerificationOutcome(
            portal=self.portal_name,
            status="UP",
            normalized={
                "gst.status": record["status"],
                "gst.legal_name": record["legal_name"],
                "financials.avg_annual_turnover": record["avg_annual_turnover"],
            },
            raw_response=record,
        )


class MockUdyamAdapter(PortalAdapter):
    portal_name = "UDYAM"

    def verify(self, udyam_number: str = "", **_: str) -> VerificationOutcome:
        record = _load("udyam.json").get(udyam_number)
        if record is None:
            return VerificationOutcome(portal=self.portal_name, status="NOT_FOUND")

        return VerificationOutcome(
            portal=self.portal_name,
            status="UP",
            normalized={
                "udyam.valid": record["valid"],
                "udyam.category": record["category"],
            },
            raw_response=record,
        )


class MockDebarmentAdapter(PortalAdapter):
    portal_name = "DEBARMENT"

    def verify(self, gstin: str = "", pan: str = "", **_: str) -> VerificationOutcome:
        record = _load("debarment.json")
        listed = gstin in record.get("listed_gstins", []) or pan in record.get("listed_pans", [])

        return VerificationOutcome(
            portal=self.portal_name,
            status="UP",
            normalized={"debarment.listed": listed},
            raw_response={"gstin": gstin, "pan": pan, "listed": listed},
        )
