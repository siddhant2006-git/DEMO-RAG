import socket
from urllib.parse import urlparse

from app.config import get_settings

settings = get_settings()


def is_redis_reachable(timeout: float = 0.5) -> bool:
    """Fast, dependency-free reachability probe — used to decide between
    enqueueing a Celery task and just running the job inline, without paying
    for Celery/kombu's own (much slower) connection retry logic."""
    parsed = urlparse(settings.redis_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
