import httpx

from app.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class OllamaError(Exception):
    pass


class OllamaClient:
    """Thin wrapper over Ollama's /api/generate.

    Temperature and seed are pinned so the same prompt against the same model
    produces the same output — required for the "run it twice, get the same
    answer" trust property, and cheap to enforce since this is the only
    place the app talks to the LLM.
    """

    def __init__(self) -> None:
        self._client = httpx.Client(base_url=settings.ollama_base_url, timeout=settings.ollama_timeout_seconds)

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = True,
        retries: int = 2,
    ) -> str:
        payload: dict = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "seed": 42},
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                response = self._client.post("/api/generate", json=payload)
                response.raise_for_status()
                return response.json()["response"]
            except (httpx.HTTPError, KeyError) as exc:
                last_error = exc
                logger.warning("ollama_request_failed", attempt=attempt, error=str(exc))

        raise OllamaError(f"Ollama request failed after {retries + 1} attempt(s): {last_error}") from last_error

    def close(self) -> None:
        self._client.close()
