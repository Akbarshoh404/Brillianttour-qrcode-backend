from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DownloadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    created_at: datetime
