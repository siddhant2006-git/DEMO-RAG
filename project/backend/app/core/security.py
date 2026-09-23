import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.errors import AppError
from app.core.deps import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _create_token(
    user: User, secret: str, expires_delta: timedelta, token_type: str
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "email": user.email,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_access_token(user: User) -> str:
    settings = get_settings()
    return _create_token(
        user,
        settings.access_token_secret,
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
    )


def create_refresh_token(user: User) -> str:
    settings = get_settings()
    return _create_token(
        user,
        settings.refresh_token_secret,
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
    )


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_token(token: str, *, token_type: str) -> dict:
    settings = get_settings()
    secret = (
        settings.access_token_secret
        if token_type == "access"
        else settings.refresh_token_secret
    )
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise AppError("INVALID_TOKEN", "Invalid or expired token", 401) from exc
    if payload.get("type") != token_type or not payload.get("sub"):
        raise AppError("INVALID_TOKEN", "Invalid or expired token", 401)
    return payload


def public_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "fullName": user.full_name,
        "isActive": user.is_active,
    }


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("AUTH_REQUIRED", "A Bearer access token is required", 401)

    payload = decode_token(credentials.credentials, token_type="access")
    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError, KeyError) as exc:
        raise AppError("INVALID_TOKEN", "Invalid or expired token", 401) from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("AUTH_REQUIRED", "User is not available", 401)
    return user
