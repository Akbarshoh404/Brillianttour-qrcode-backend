from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, computed_field


class DocumentResponse(BaseModel):
    """Public representation of a document.

    Notably absent: `storage_path`. The underlying Supabase storage location
    is an implementation detail and must never be exposed to the client.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    uuid: uuid_lib.UUID
    title: str
    file_size: int
    created_at: datetime
    updated_at: datetime
    total_scans: int
    total_downloads: int
    last_scan: datetime | None = None
    last_download: datetime | None = None

    is_active: bool
    deleted_at: datetime | None = None
    purge_at: datetime | None = None

    domain_id: int | None = None
    domain_name: str | None = None
    folder_id: int | None = None
    folder_name: str | None = None

    # Populated by the service layer from PUBLIC_BASE_URL — never hardcoded.
    qr_url: str
    view_url: str
    download_url: str
    qr_link: str

    @computed_field  # type: ignore[misc]
    @property
    def file_size_readable(self) -> str:
        size = float(self.file_size)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class DocumentListResponse(BaseModel):
    items: List[DocumentResponse]
    total: int
    storage_used_bytes: int
