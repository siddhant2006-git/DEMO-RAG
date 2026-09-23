from app.config import get_settings
from app.core.errors import AppError
from app.services.verification.adapters.gst import GstAdapter
from app.services.verification.adapters.mock_portal import (
    MockDebarmentAdapter,
    MockGstAdapter,
    MockUdyamAdapter,
)
from app.services.verification.adapters.udyam import UdyamAdapter
from app.services.verification.base import PortalAdapter

settings = get_settings()

_MOCK_ADAPTERS: dict[str, type[PortalAdapter]] = {
    "GST": MockGstAdapter,
    "UDYAM": MockUdyamAdapter,
    "DEBARMENT": MockDebarmentAdapter,
}

# DEBARMENT has no live adapter yet — deliberately: see "what not to build".
# It stays mock-only in both modes so a missing live source degrades to
# NEEDS-REVIEW rather than silently skipping the debarment check.
_LIVE_ADAPTERS: dict[str, type[PortalAdapter]] = {
    "GST": GstAdapter,
    "UDYAM": UdyamAdapter,
    "DEBARMENT": MockDebarmentAdapter,
}


def get_adapter(portal: str) -> PortalAdapter:
    """Adding a new portal = adding one adapter file + one entry here."""
    portal = portal.upper()
    registry = _MOCK_ADAPTERS if settings.verification_mode == "mock" else _LIVE_ADAPTERS
    adapter_cls = registry.get(portal)
    if adapter_cls is None:
        raise AppError("UNKNOWN_PORTAL", f"No adapter registered for portal '{portal}'", 400)
    return adapter_cls()
