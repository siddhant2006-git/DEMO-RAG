from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx


@dataclass
class PortalResponseResult:
    status: str
    reason: str = ""
    data: dict = field(default_factory=dict)


def verify_portal_response(response: httpx.Response) -> PortalResponseResult:
    status_code = response.status_code
    if status_code == 403:
        return PortalResponseResult(
            status="NEEDS-REVIEW",
            reason=f"Portal access forbidden (HTTP {status_code})",
        )
    if status_code == 404:
        return PortalResponseResult(
            status="NOT_FOUND", reason=f"Portal record not found (HTTP {status_code})"
        )
    if not 200 <= status_code < 300:
        return PortalResponseResult(
            status="DOWN", reason=f"Portal returned HTTP {status_code}"
        )
    try:
        data = response.json()
    except ValueError:
        return PortalResponseResult(
            status="DOWN", reason="Portal returned invalid JSON"
        )
    if not isinstance(data, dict):
        return PortalResponseResult(
            status="DOWN", reason="Portal returned an invalid response"
        )
    return PortalResponseResult(status="UP", data=data)


@dataclass
class VerificationOutcome:
    portal: str
    # UP: portal reached, record found | NOT_FOUND: portal reached, no record
    # | NEEDS-REVIEW: portal denied access | DOWN: unreachable / not configured
    # Never PASS or FAIL here — that judgement belongs to the rule engine, not
    # the verification layer.
    status: str
    normalized: dict = field(default_factory=dict)
    raw_response: dict = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class PortalAdapter(ABC):
    portal_name: str

    @abstractmethod
    def verify(self, **identifiers: str) -> VerificationOutcome:
        """Look up a vendor's record on this portal.

        Implementations map missing records, denied access, and outages to
        NOT_FOUND, NEEDS-REVIEW, and DOWN so portal failures cannot create false
        PASS/FAIL results or crash the verification run.
        """
        raise NotImplementedError
