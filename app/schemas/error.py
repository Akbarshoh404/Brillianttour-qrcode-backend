from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Consistent JSON error shape returned by every API error."""

    detail: str
    code: str
    context: Any | None = None
