import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.services.verification.base import PortalAdapter, VerificationOutcome

settings = get_settings()
logger = get_logger(__name__)


class UdyamAdapter(PortalAdapter):
    """Live Udyam registration lookup. Same contract as GstAdapter: without
    UDYAM_API_BASE_URL / UDYAM_API_KEY configured it degrades to status=DOWN
    instead of raising."""

    portal_name = "UDYAM"

    def verify(self, udyam_number: str = "", **_: str) -> VerificationOutcome:
        if not settings.udyam_api_base_url or not settings.udyam_api_key:
            logger.warning("udyam_adapter_not_configured")
            return VerificationOutcome(portal=self.portal_name, status="DOWN", raw_response={"reason": "not_configured"})

        try:
            response = httpx.get(
                f"{settings.udyam_api_base_url}/udyam/{udyam_number}",
                headers={"Authorization": f"Bearer {settings.udyam_api_key}"},
                timeout=10.0,
            )
            if response.status_code == 404:
                return VerificationOutcome(portal=self.portal_name, status="NOT_FOUND")
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            logger.warning("udyam_adapter_request_failed", error=str(exc))
            return VerificationOutcome(portal=self.portal_name, status="DOWN", raw_response={"error": str(exc)})

        return VerificationOutcome(
            portal=self.portal_name,
            status="UP",
            normalized={
                "udyam.valid": data.get("valid"),
                "udyam.category": data.get("category"),
            },
            raw_response=data,
        )
