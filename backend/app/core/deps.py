from fastapi import Header

from app.db.session import get_db

__all__ = ["get_db", "get_actor"]


def get_actor(x_actor: str | None = Header(default=None)) -> str:
    """Identifies who performed an action for the audit log.

    There is no auth system yet, so this is a stand-in: the frontend can send
    an X-Actor header (the officer's name); it defaults to "officer" when
    absent, which is fine for the single-user demo this project targets.
    """
    return x_actor or "officer"
