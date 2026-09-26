import httpx

from app.config import get_settings
from app.core.logging import get_logger
from app.services.verification.base import (
    PortalAdapter,
    VerificationOutcome,
    verify_portal_response,
)

settings = get_settings()
logger = get_logger(__name__)


class GstAdapter(PortalAdapter):
    """Live GST portal lookup. Requires GST_API_BASE_URL / GST_API_KEY to be
    configured (a KYC/verification provider, since the government GST portal
    has no public unauthenticated API) — without them this degrades to
    status=DOWN, which the rule engine treats as NEEDS-REVIEW rather than a
    false PASS or FAIL.
    """

    portal_name = "GST"

    def verify(self, gstin: str = "", **_: str) -> VerificationOutcome:
        if not settings.gst_api_base_url or not settings.gst_api_key:
            logger.warning("gst_adapter_not_configured")
            return VerificationOutcome(
                portal=self.portal_name,
                status="DOWN",
                raw_response={"reason": "not_configured"},
            )

        try:
            response = httpx.get(
                f"{settings.gst_api_base_url}/gstin/{gstin}",
                headers={"Authorization": f"Bearer {settings.gst_api_key}"},
                timeout=10.0,
            )
            result = verify_portal_response(response)
            if result.status != "UP":
                return VerificationOutcome(
                    portal=self.portal_name,
                    status=result.status,
                    raw_response={"reason": result.reason},
                )
            data = result.data
        except httpx.HTTPError as exc:
            logger.warning("gst_adapter_request_failed", error=str(exc))
            return VerificationOutcome(
                portal=self.portal_name, status="DOWN", raw_response={"error": str(exc)}
            )

        return VerificationOutcome(
            portal=self.portal_name,
            status="UP",
            normalized={
                "gst.status": data.get("status"),
                "gst.legal_name": data.get("legal_name"),
                "financials.avg_annual_turnover": data.get("avg_annual_turnover"),
            },
            raw_response=data,
        )
