from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database.session import get_db
from app.services.auth_service import decode_access_token

__all__ = ["get_db", "get_current_admin"]

_bearer_scheme = HTTPBearer(auto_error=True, description="Dashboard login token")


def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme)) -> str:
    """Protects dashboard actions (list/create/replace/delete/etc).

    Never apply this to /p/{uuid} or /download/{uuid} — those must stay
    reachable by anyone with the QR code or link, no login required.
    """
    return decode_access_token(credentials.credentials)
