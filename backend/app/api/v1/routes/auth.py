import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.deps import get_current_user, get_db, get_optional_current_user
from app.core.errors import AppError
from app.core.logging import get_logger
from app.models.auth import PasswordResetToken, RefreshSession, User, VerificationToken
from app.schemas.auth import (
    EmailTokenRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageOut,
    RegisterRequest,
    ResetPasswordRequest,
    UserOut,
)
from app.services.auth.email import EmailDeliveryError, send_auth_email
from app.services.auth.rate_limit import check_rate_limit
from app.services.auth.security import (
    cookie_kwargs,
    create_access_token,
    hash_password,
    new_token,
    token_hash,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)


def _set_auth_cookies(
    response: Response, access_token: str, refresh_token: str
) -> None:
    try:
        kwargs = cookie_kwargs()
        response.set_cookie(
            "access_token",
            access_token,
            max_age=get_settings().access_token_minutes * 60,
            **kwargs,
        )
        response.set_cookie(
            "refresh_token",
            refresh_token,
            max_age=get_settings().refresh_token_days * 86400,
            **kwargs,
        )
    except (TypeError, ValueError, UnicodeError) as exc:
        raise AppError(
            "AUTH_COOKIE_CONFIGURATION_ERROR",
            "Authentication cookie configuration is invalid.",
            500,
        ) from exc


def _clear_auth_cookies(response: Response) -> None:
    try:
        kwargs = cookie_kwargs()
        response.delete_cookie("access_token", **kwargs)
        response.delete_cookie("refresh_token", **kwargs)
    except (TypeError, ValueError, UnicodeError) as exc:
        raise AppError(
            "AUTH_COOKIE_CONFIGURATION_ERROR",
            "Authentication cookie configuration is invalid.",
            500,
        ) from exc


def _new_verification_token(db: Session, user: User) -> str:
    raw_token = new_token()
    db.add(
        VerificationToken(
            user_id=user.id,
            token_hash=token_hash(raw_token),
            expires_at=datetime.now(UTC)
            + timedelta(hours=get_settings().email_verification_hours),
        )
    )
    return raw_token


def _verification_url(raw_token: str) -> str:
    return f"{get_settings().frontend_url}/verify-email?token={raw_token}"


def _ensure_email_verified(user: User, environment: str) -> None:
    if user.email_verified_at is not None:
        return
    if environment.lower() != "development":
        raise AppError("EMAIL_NOT_VERIFIED", "Verify your email before signing in", 403)
    user.email_verified_at = datetime.now(UTC)


@router.post("/register", response_model=MessageOut, status_code=201)
def register(
    payload: RegisterRequest, request: Request, db: Session = Depends(get_db)
) -> MessageOut:
    check_rate_limit(
        "registration",
        request.client.host if request.client else "unknown",
        get_settings().rate_limit_registration_attempts,
    )
    try:
        payload.validate_match()
    except ValueError as exc:
        raise AppError("PASSWORD_MISMATCH", str(exc), 422) from exc
    email = str(payload.email).lower()
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise AppError(
            "EMAIL_ALREADY_REGISTERED", "An account with this email already exists", 409
        )
    settings = get_settings()
    development_mode = settings.environment.lower() == "development"
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        company_name=payload.company_name,
        vendor_id=payload.vendor_id,
        authorized_person_name=payload.authorized_person_name,
        mobile_number=payload.mobile_number,
        gstin=payload.gstin,
        pan=payload.pan,
        udyam_number=payload.udyam_number,
        email_verified_at=datetime.now(UTC) if development_mode else None,
    )
    try:
        db.add(user)
        db.flush()
        if not development_mode:
            raw_token = _new_verification_token(db, user)
            verification_url = _verification_url(raw_token)
            if not settings.smtp_host:
                raise EmailDeliveryError("SMTP is not configured")
            send_auth_email(
                recipient=email,
                subject="Verify your TenderGuard email",
                link=verification_url,
            )
        db.commit()
    except EmailDeliveryError as exc:
        db.rollback()
        raise AppError(
            "EMAIL_DELIVERY_FAILED",
            "We could not send the verification email. Please try again later.",
            503,
        ) from exc
    except IntegrityError as exc:
        db.rollback()
        if db.scalar(select(User.id).where(User.email == email)) is not None:
            raise AppError(
                "EMAIL_ALREADY_REGISTERED",
                "An account with this email already exists",
                409,
            ) from exc
        raise
    return MessageOut(
        message=(
            "Registration successful. You can now sign in."
            if development_mode
            else "Registration successful. Check your email to verify your account."
        ),
    )


@router.post("/resend-verification", response_model=MessageOut)
def resend_verification(
    payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)
) -> MessageOut:
    check_rate_limit(
        "verification-resend",
        request.client.host if request.client else "unknown",
        3,
    )
    generic_message = "If an unverified account exists for that email, a verification link has been sent."
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or user.email_verified_at is not None:
        return MessageOut(message=generic_message)

    settings = get_settings()
    try:
        for old_token in user.verification_tokens:
            if old_token.used_at is None:
                old_token.used_at = datetime.now(UTC)
        raw_token = _new_verification_token(db, user)
        verification_url = _verification_url(raw_token)
        if settings.smtp_host:
            send_auth_email(
                recipient=user.email,
                subject="Verify your TenderGuard email",
                link=verification_url,
            )
        elif settings.environment.lower() != "development":
            raise EmailDeliveryError("SMTP is not configured")
        db.commit()
    except EmailDeliveryError:
        db.rollback()
        logger.warning("verification_email_delivery_failed")
        return MessageOut(message=generic_message)

    return MessageOut(
        message=generic_message,
        verification_url=verification_url if not settings.smtp_host else None,
    )


@router.post("/login", response_model=UserOut)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    check_rate_limit(
        "login",
        request.client.host if request.client else "unknown",
        get_settings().rate_limit_login_attempts,
    )
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError("INVALID_CREDENTIALS", "Email or password is incorrect", 401)
    if not user.is_active:
        raise AppError("ACCOUNT_DISABLED", "This account is disabled", 403)
    _ensure_email_verified(user, get_settings().environment)
    raw_refresh = new_token()
    db.add(
        RefreshSession(
            user_id=user.id,
            token_hash=token_hash(raw_refresh),
            expires_at=datetime.now(UTC)
            + timedelta(days=get_settings().refresh_token_days),
        )
    )
    _set_auth_cookies(
        response, create_access_token(str(user.id), user.role), raw_refresh
    )
    db.commit()
    return user


@router.post("/logout", response_model=MessageOut)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> MessageOut:
    # The token is read from the cookie explicitly so it is never returned or logged.
    token = refresh_token
    if token:
        session = db.scalar(
            select(RefreshSession).where(RefreshSession.token_hash == token_hash(token))
        )
        if session is not None:
            session.revoked_at = datetime.now(UTC)
            db.commit()
    _clear_auth_cookies(response)
    return MessageOut(message="Signed out")


@router.post("/refresh", response_model=UserOut)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Authentication required")
    session = db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_hash(refresh_token)
        )
    )
    now = datetime.now(UTC)
    if (
        session is None
        or session.revoked_at is not None
        or _is_expired(session.expires_at)
        or not session.user.is_active
    ):
        _clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Session expired")
    session.revoked_at = now
    next_refresh = new_token()
    db.add(
        RefreshSession(
            user_id=session.user_id,
            token_hash=token_hash(next_refresh),
            expires_at=now + timedelta(days=get_settings().refresh_token_days),
        )
    )
    _set_auth_cookies(
        response,
        create_access_token(str(session.user.id), session.user.role),
        next_refresh,
    )
    db.commit()
    return session.user


@router.post("/verify-email", response_model=MessageOut)
def verify_email(
    payload: EmailTokenRequest, db: Session = Depends(get_db)
) -> MessageOut:
    token = db.scalar(
        select(VerificationToken).where(
            VerificationToken.token_hash == token_hash(payload.token)
        )
    )
    if token is None or token.used_at is not None or _is_expired(token.expires_at):
        raise AppError(
            "INVALID_VERIFICATION_TOKEN", "Verification link is invalid or expired", 400
        )
    token.used_at = datetime.now(UTC)
    token.user.email_verified_at = datetime.now(UTC)
    db.commit()
    return MessageOut(message="Email verified. You can now sign in.")


@router.post("/forgot-password", response_model=MessageOut)
def forgot_password(
    payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)
) -> MessageOut:
    check_rate_limit(
        "password-reset", request.client.host if request.client else "unknown", 3
    )
    user = db.scalar(select(User).where(User.email == str(payload.email).lower()))
    if user is not None:
        try:
            raw_token = new_token()
            db.add(
                PasswordResetToken(
                    user_id=user.id,
                    token_hash=token_hash(raw_token),
                    expires_at=datetime.now(UTC)
                    + timedelta(minutes=get_settings().password_reset_minutes),
                )
            )
            send_auth_email(
                recipient=user.email,
                subject="Reset your TenderGuard password",
                link=f"{get_settings().frontend_url}/reset-password?token={raw_token}",
            )
            db.commit()
        except EmailDeliveryError:
            db.rollback()
            logger.warning("password_reset_email_delivery_failed")
            return MessageOut(
                message="If an account exists for that email, a reset link has been sent."
            )
    return MessageOut(
        message="If an account exists for that email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageOut)
def reset_password(
    payload: ResetPasswordRequest, response: Response, db: Session = Depends(get_db)
) -> MessageOut:
    try:
        payload.validate_match()
    except ValueError as exc:
        raise AppError("PASSWORD_MISMATCH", str(exc), 422) from exc
    reset = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash(payload.token)
        )
    )
    if reset is None or reset.used_at is not None or _is_expired(reset.expires_at):
        raise AppError("INVALID_RESET_TOKEN", "Reset link is invalid or expired", 400)
    reset.used_at = datetime.now(UTC)
    reset.user.password_hash = hash_password(payload.password)
    for session in reset.user.sessions:
        session.revoked_at = datetime.now(UTC)
    db.commit()
    _clear_auth_cookies(response)
    return MessageOut(message="Password updated. You can now sign in.")


@router.get("/me", response_model=UserOut | None)
def me(user: User | None = Depends(get_optional_current_user)) -> User | None:
    return user
