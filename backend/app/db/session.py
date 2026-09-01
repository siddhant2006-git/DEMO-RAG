from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# create_engine() does not open a connection — it connects lazily on first use,
# so importing this module never requires the database to be reachable.
# connect_timeout keeps a dead/unreachable database from hanging a request for
# minutes (e.g. a firewall silently dropping SYNs) — it fails fast instead.
# sqlite3's DBAPI has no connect_timeout param, and check_same_thread must be
# disabled since SessionLocal() instances are used across FastAPI's threadpool.
is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {"connect_timeout": 3}

engine = create_engine(
    settings.resolved_database_url,
    pool_pre_ping=True,
    future=True,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
