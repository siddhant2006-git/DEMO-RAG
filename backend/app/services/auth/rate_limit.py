from collections import defaultdict
from threading import Lock
from time import monotonic

from app.config import get_settings
from app.core.errors import AppError

_attempts: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def check_rate_limit(scope: str, key: str, limit: int) -> None:
    now = monotonic()
    window = get_settings().rate_limit_window_seconds
    bucket_key = f"{scope}:{key}"
    with _lock:
        valid = [
            timestamp for timestamp in _attempts[bucket_key] if now - timestamp < window
        ]
        if len(valid) >= limit:
            raise AppError(
                "RATE_LIMITED",
                "Too many attempts. Please try again later.",
                429,
            )
        valid.append(now)
        _attempts[bucket_key] = valid
