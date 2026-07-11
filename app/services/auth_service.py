"""
Single-admin JWT authentication for the dashboard.

There are no user accounts and no registration — this is one shared
credential (set via ADMIN_USERNAME / ADMIN_PASSWORD env vars) gating access
to the dashboard's document management actions. It intentionally does NOT
gate the public /p/{uuid} and /download/{uuid} routes — anyone with a QR
code or link must always be able to reach the PDF without logging in.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status

from app.config import settings

ALGORITHM = "HS256"


def _require_configured() -> None:
    if not settings.ADMIN_PASSWORD or not settings.JWT_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth is not configured on the server. Set ADMIN_PASSWORD and JWT_SECRET_KEY.",
        )


def verify_credentials(username: str, password: str) -> bool:
    _require_configured()
    valid_username = secrets.compare_digest(username, settings.ADMIN_USERNAME)
    valid_password = secrets.compare_digest(password, settings.ADMIN_PASSWORD)
    return valid_username and valid_password


def create_access_token(username: str) -> str:
    _require_configured()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expires_at}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    """Returns the username encoded in a valid token, or raises HTTPException(401)."""
    _require_configured()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")
        return username
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.") from exc
