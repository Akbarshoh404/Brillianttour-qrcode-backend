from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    country: str | None
    city: str | None
    region: str | None
    isp: str | None
    latitude: float | None
    longitude: float | None
    timezone: str | None
    browser: str | None
    operating_system: str | None
    device: str | None
    user_agent: str | None
    ip: str | None
    referrer: str | None
    language: str | None
    created_at: datetime


class ScanBreakdownEntry(BaseModel):
    label: str
    count: int


class ScanSummaryResponse(BaseModel):
    total_scans: int
    by_country: list[ScanBreakdownEntry]
    by_device: list[ScanBreakdownEntry]
    by_browser: list[ScanBreakdownEntry]
    recent: list[ScanResponse]
