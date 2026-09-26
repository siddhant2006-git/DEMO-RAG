# Authentication and Portal Error Notes

## Email Verification

In development, newly registered accounts are automatically verified. Existing development accounts are automatically verified after correct credentials are entered. This removes the local SMTP/email-link blocker.

In non-development environments, email verification remains required. Registration sends a verification link using SMTP, login rejects unverified accounts with `EMAIL_NOT_VERIFIED`, and missing SMTP configuration is treated as an email-delivery failure.

After changing backend routes, restart the backend server before testing registration or login.

## Login `/auth/me` anonymous session

This request checks for an existing signed-in session during app startup. When no valid access cookie exists, the endpoint returns `200` with `null`, and the frontend treats the user as signed out. Protected endpoints continue to return `401` when authentication is missing or invalid.

## Portal HTTP `403`

Live GST and Udyam HTTP responses are classified by `verify_portal_response`. A portal `403` becomes `NEEDS-REVIEW` and records a reason containing the HTTP status, rather than being treated as a verified record or crashing the lookup. The live adapters use this classification.

## Other defensive handling

- Rate-limit responses use a structured `429 RATE_LIMITED` application error.
- Database failures are logged without exposing SQL internals and return a safe `503 DATABASE_ERROR` response. Request-scoped DB sessions roll back on exceptions.
- Failed authentication-email delivery does not silently claim that an email was sent. Password-reset responses remain generic to avoid disclosing whether an account exists.
- Token expiry comparisons normalize naive timestamps, which can be returned by SQLite, before comparing them with UTC time.
- Cookie configuration failures return a stable auth-cookie error instead of leaking an exception detail.

## Tests and validation

Focused tests cover portal `403` classification, development and production verification behavior, rate-limit errors, missing SMTP configuration, and naive SQLite expiry timestamps. The frontend production build and editor diagnostics passed during the implementation. Run the focused backend tests from `backend/` with the project-root virtual environment:

```bash
../.venv/Scripts/python.exe -m pytest tests/test_verification_response.py tests/test_auth_error_handling.py -q
```
