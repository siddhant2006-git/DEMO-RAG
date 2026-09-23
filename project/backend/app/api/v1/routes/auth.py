from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    hash_password,
    public_user,
    token_hash,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalise_identifier(value: str) -> str:
    return value.strip().lower()


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    username = payload.username.strip().lower()
    email = str(payload.email).strip().lower()
    existing = db.scalar(
        select(User).where(or_(User.username == username, User.email == email))
    )
    if existing:
        field = "username" if existing.username == username else "email"
        raise AppError(
            "ALREADY_EXISTS", f"A user with this {field} already exists", 409
        )

    user = User(
        username=username,
        email=email,
        full_name=payload.fullName.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            "ALREADY_EXISTS", "Username or email is already registered", 409
        ) from exc
    db.refresh(user)
    return {"user": public_user(user)}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:
    identifier = _normalise_identifier(payload.identifier)
    user = db.scalar(
        select(User).where(or_(User.username == identifier, User.email == identifier))
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Invalid username/email or password", 401)

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    user.refresh_token_hash = token_hash(refresh_token)
    db.commit()
    return {
        "user": public_user(user),
        "accessToken": access_token,
        "refreshToken": refresh_token,
    }


@router.post("/refresh")
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict:
    token_payload = decode_token(payload.refreshToken, token_type="refresh")
    try:
        user_id = UUID(token_payload["sub"])
    except (ValueError, TypeError) as exc:
        raise AppError(
            "INVALID_REFRESH_TOKEN", "Invalid or expired refresh token", 401
        ) from exc
    user = db.get(User, user_id)
    if (
        user is None
        or not user.is_active
        or user.refresh_token_hash != token_hash(payload.refreshToken)
    ):
        raise AppError("INVALID_REFRESH_TOKEN", "Invalid or expired refresh token", 401)
    return {"accessToken": create_access_token(user)}


@router.post("/logout")
def logout(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict:
    user.refresh_token_hash = None
    db.commit()
    return {"message": "Logged out successfully"}


@router.get("/me")
def current_user(user: User = Depends(get_current_user)) -> dict:
    return {"user": public_user(user)}
