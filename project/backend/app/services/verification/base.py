from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class VerificationOutcome:
    portal: str
    # UP: portal reached, record found | NOT_FOUND: portal reached, no record
    # | DOWN: portal unreachable / not configured / errored
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

        Implementations must never raise for "record not found" or "portal
        unreachable" — those map to status NOT_FOUND / DOWN respectively, so a
        flaky government portal degrades a finding to NEEDS-REVIEW instead of
        crashing the verification run.
        """
        raise NotImplementedError
