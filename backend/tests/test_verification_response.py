from types import SimpleNamespace

from app.services.verification.base import verify_portal_response


def mock_portal(status_code: int) -> SimpleNamespace:
    return SimpleNamespace(status_code=status_code)


def test_portal_403_returns_needs_review():
    response = mock_portal(status_code=403)

    result = verify_portal_response(response)

    assert result.status == "NEEDS-REVIEW"
    assert "403" in result.reason
