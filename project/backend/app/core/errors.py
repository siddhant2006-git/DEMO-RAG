import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for domain errors that should map to a clean HTTP response."""

    def __init__(self, code: str, message: str, status_code: int = 400, detail: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail or {}
        super().__init__(message)


def parse_uuid(value: str, *, field: str = "id") -> uuid.UUID:
    """Parses a request-supplied id, raising a clean 400 AppError instead of
    letting an unhandled ValueError from uuid.UUID() surface as a 500 — e.g.
    a stale/missing id from a frontend session that lost its tender/bid id."""
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise AppError("INVALID_ID", f"'{value}' is not a valid {field}", 400) from exc


def _envelope(code: str, message: str, detail: dict | None = None) -> dict:
    return {"code": code, "message": message, "detail": detail or {}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.warning("app_error", code=exc.code, message=exc.message, path=request.url.path)
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope("VALIDATION_ERROR", "Request validation failed", {"errors": exc.errors()}),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope("HTTP_ERROR", str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_error", path=request.url.path, exc_info=exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("INTERNAL_ERROR", "An unexpected error occurred"),
        )
