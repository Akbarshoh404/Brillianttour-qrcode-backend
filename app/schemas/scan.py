from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    country: str | None
    city: str | None
    browser: str | None
    operating_system: str | None
    device: str | None
    user_agent: str | None
    ip: str | None
    created_at: datetime
