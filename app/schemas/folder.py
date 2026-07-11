from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FolderCreate(BaseModel):
    name: str


class FolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime
    document_count: int = 0


class FolderListResponse(BaseModel):
    items: list[FolderResponse]


class FolderMoveRequest(BaseModel):
    folder_id: int | None = None
