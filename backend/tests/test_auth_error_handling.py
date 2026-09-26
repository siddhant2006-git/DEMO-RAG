from collections import defaultdict
from datetime import UTC, datetime, timedelta
import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.routes.auth import _ensure_email_verified, _is_expired
from app.core.errors import (
    AppError,
    _safe_validation_errors,
    register_exception_handlers,
)
from app.schemas.auth import RegisterRequest
from app.core.deps import get_optional_current_user
from app.services.auth import email, rate_limit


def test_expiry_comparison_accepts_naive_sqlite_timestamp():
    expired = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)

    assert _is_expired(expired)


def test_optional_current_user_returns_none_without_cookie():
    assert get_optional_current_user(access_token=None, db=object()) is None


def test_development_login_auto_verifies_account():
    user = SimpleNamespace(email_verified_at=None)

    _ensure_email_verified(user, "development")

    assert user.email_verified_at is not None


def test_production_login_still_requires_email_verification():
    user = SimpleNamespace(email_verified_at=None)

    with pytest.raises(AppError) as raised:
        _ensure_email_verified(user, "production")

    assert raised.value.code == "EMAIL_NOT_VERIFIED"
    assert raised.value.status_code == 403


def test_validation_error_details_are_serializable_and_hide_input():
    password = "7669886289AA##"
    errors = _safe_validation_errors(
        [
            {
                "type": "value_error",
                "loc": ("body", "password"),
                "msg": "Password is invalid",
                "input": password,
                "ctx": {"error": ValueError("Password is invalid")},
            }
        ]
    )

    encoded = json.dumps(errors)

    assert "ValueError" not in encoded
    assert password not in encoded
    assert errors[0]["loc"] == ["body", "password"]


def test_invalid_registration_returns_422_instead_of_500():
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/register")
    def register(payload: RegisterRequest):
        return {"email": payload.email}

    response = TestClient(app).post(
        "/register",
        json={
            "company_name": "Test Company",
            "vendor_id": "TEST-001",
            "authorized_person_name": "Test User",
            "email": "vendor@example.com",
            "mobile_number": "+911234567890",
            "pan": "1234447393i",
            "password": "7669886289AA##",
            "confirm_password": "7669886289AA##",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    response_text = response.text
    assert "7669886289AA##" not in response_text
    assert "ValueError" not in response_text


def test_email_sender_reports_missing_smtp_configuration(monkeypatch):
    monkeypatch.setattr(email, "get_settings", lambda: SimpleNamespace(smtp_host=None))

    with pytest.raises(email.EmailDeliveryError, match="SMTP is not configured"):
        email.send_auth_email(
            recipient="vendor@example.com",
            subject="Verify account",
            link="http://localhost/verify-email?token=token",
        )


def test_rate_limit_uses_structured_429_error(monkeypatch):
    monkeypatch.setattr(
        rate_limit,
        "get_settings",
        lambda: SimpleNamespace(rate_limit_window_seconds=60),
    )
    monkeypatch.setattr(rate_limit, "_attempts", defaultdict(list))

    rate_limit.check_rate_limit("login", "test-client", 1)
    with pytest.raises(AppError) as raised:
        rate_limit.check_rate_limit("login", "test-client", 1)

    assert raised.value.code == "RATE_LIMITED"
    assert raised.value.status_code == 429
