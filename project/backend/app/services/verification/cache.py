import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.verification import VerificationResult
from app.services.verification.registry import get_adapter

settings = get_settings()


def verify_with_cache(
    db: Session, *, bid_id: uuid.UUID, portal: str, identifiers: dict
) -> VerificationResult:
    """Reuses a cached VerificationResult within VERIFICATION_CACHE_TTL_SECONDS
    instead of hitting the portal again — keeps repeat checks (e.g. re-running
    the rule engine after an officer edits a requirement) fast and avoids
    tripping a real portal's rate limit."""
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.verification_cache_ttl_seconds)

    existing = db.execute(
        select(VerificationResult)
        .where(VerificationResult.bid_id == bid_id, VerificationResult.portal == portal.upper())
        .order_by(VerificationResult.fetched_at.desc())
    ).scalars().first()

    if existing is not None:
        # SQLite has no native timezone-aware storage, so DateTime(timezone=True)
        # round-trips as naive UTC there (unlike Postgres) — normalize before
        # comparing so this works under either dialect.
        fetched_at = existing.fetched_at
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=UTC)
        if fetched_at >= cutoff:
            return existing

    outcome = get_adapter(portal).verify(**identifiers)

    result = VerificationResult(
        bid_id=bid_id,
        portal=outcome.portal,
        status=outcome.status,
        normalized=outcome.normalized,
        raw_response=outcome.raw_response,
        fetched_at=outcome.fetched_at,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result
