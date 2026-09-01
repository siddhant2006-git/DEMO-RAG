from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> backend/ -> project/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Anchored to this file's directory (backend/), not the process cwd —
        # otherwise scripts invoked from the project root silently miss .env
        # and fall back to the Postgres defaults below.
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "TenderGuard"
    environment: str = "development"
    debug: bool = True

    database_url: str = "postgresql+psycopg://tenderguard:tenderguard@localhost:5432/tenderguard"

    redis_url: str = "redis://localhost:6379/0"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: int = 120

    # Path to tesseract.exe — only needed on Windows when it isn't on PATH
    # (e.g. the UB-Mannheim installer default: C:\Program Files\Tesseract-OCR\tesseract.exe)
    tesseract_cmd: str | None = None

    verification_mode: str = "mock"  # mock | live
    verification_cache_ttl_seconds: int = 3600

    # Live portal credentials — per "what not to build", only GST and Udyam
    # get real integrations; everything else stays mock-only. Left unset here,
    # the live adapters degrade to status=DOWN rather than erroring.
    gst_api_base_url: str | None = None
    gst_api_key: str | None = None
    udyam_api_base_url: str | None = None
    udyam_api_key: str | None = None

    upload_dir: str = "./data/uploads"
    vectorstore_dir: str = "./data/vectorstore"
    mock_portal_dir: str = "./data/mock_portals"
    max_upload_mb: int = 50

    cors_origins: str = "http://localhost:5173"

    @field_validator("upload_dir", "vectorstore_dir", "mock_portal_dir", mode="after")
    @classmethod
    def _resolve_data_dir(cls, v: str) -> str:
        # Anchored to the project root, not the process cwd — a relative
        # value like "../data/uploads" must resolve the same way whether a
        # script is run from backend/ (uvicorn, celery) or the project root
        # (scripts/*.py).
        p = Path(v)
        return str(p if p.is_absolute() else (PROJECT_ROOT / v).resolve())

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def resolved_database_url(self) -> str:
        """database_url with a relative sqlite:/// path anchored to the
        project root instead of the process cwd — used by both app/db/session.py
        and migrations/env.py so `alembic upgrade head` and the running app
        always point at the same file regardless of which directory they run from."""
        prefix = "sqlite:///"
        if not self.database_url.startswith(prefix):
            return self.database_url
        raw_path = self.database_url[len(prefix):]
        if not raw_path or Path(raw_path).is_absolute():
            return self.database_url
        return prefix + str((PROJECT_ROOT / raw_path).resolve())

    def ensure_dirs(self) -> None:
        for d in (self.upload_dir, self.vectorstore_dir, self.mock_portal_dir):
            Path(d).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
