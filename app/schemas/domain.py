from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DomainCreate(BaseModel):
    name: str
    base_url: str


class DomainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # None identifies the implicit "default" domain — PUBLIC_BASE_URL from
    # the environment, not a real row in the domains table.
    id: int | None
    name: str
    base_url: str
    created_at: datetime | None = None
    is_default: bool = False


class DomainListResponse(BaseModel):
    items: list[DomainResponse]
