import json

from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger
from app.services.llm.client import OllamaClient

logger = get_logger(__name__)


class SchemaExtractionError(Exception):
    pass


def extract_structured(
    client: OllamaClient,
    prompt: str,
    schema: type[BaseModel],
    *,
    system: str | None = None,
    max_repairs: int = 2,
) -> BaseModel:
    """Runs `prompt`, forces JSON output, and validates it against `schema`.

    On invalid JSON or a schema mismatch, sends the model its own bad output
    plus the error and the schema, asking it to fix it — repeated up to
    max_repairs times before giving up loudly rather than returning
    best-effort garbage.
    """
    raw = client.generate(prompt, system=system, json_mode=True)
    last_error: Exception | None = None

    for attempt in range(max_repairs + 1):
        try:
            data = json.loads(raw)
            return schema.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            logger.warning("json_guard_repair_attempt", attempt=attempt, error=str(exc))
            if attempt == max_repairs:
                break
            repair_prompt = (
                "The JSON below is invalid or does not match the required schema.\n\n"
                f"Error: {exc}\n\n"
                f"Required JSON schema:\n{json.dumps(schema.model_json_schema())}\n\n"
                f"Invalid output:\n{raw}\n\n"
                "Return ONLY corrected JSON matching the schema. No prose, no markdown fences."
            )
            raw = client.generate(repair_prompt, system=system, json_mode=True)

    raise SchemaExtractionError(
        f"Could not obtain schema-valid JSON after {max_repairs + 1} attempt(s): {last_error}"
    )
