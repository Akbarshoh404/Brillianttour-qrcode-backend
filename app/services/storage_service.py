"""
Wraps all interaction with Supabase Storage.

This is the ONLY module in the codebase allowed to talk to the Supabase
Storage API directly. Nothing outside this service should ever construct a
Supabase URL — QR codes and redirects are built from PUBLIC_BASE_URL instead
(see app/services/qr_service.py and app/api/routes/redirect.py).
"""
from __future__ import annotations

import logging

from fastapi import HTTPException, status
from supabase import Client, create_client

from app.config import settings

logger = logging.getLogger(__name__)

SIGNED_URL_TTL_SECONDS = 60 * 60  # 1 hour, freshly minted on every request


class StorageService:
    def __init__(self) -> None:
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        if self._client is None:
            self._client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        return self._client

    @property
    def bucket(self):
        return self.client.storage.from_(settings.SUPABASE_STORAGE_BUCKET)

    def upload(self, path: str, contents: bytes, content_type: str = "application/pdf") -> None:
        try:
            self.bucket.upload(
                path=path,
                file=contents,
                file_options={"content-type": content_type, "upsert": "true"},
            )
        except Exception as exc:  # noqa: BLE001 - surface as a clean API error
            logger.exception("Failed to upload object to storage: %s", path)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to upload file to storage. Please try again.",
            ) from exc

    def delete(self, path: str) -> None:
        try:
            self.bucket.remove([path])
        except Exception:  # noqa: BLE001 - best-effort cleanup, never block the caller
            logger.warning("Failed to delete storage object (continuing): %s", path)

    def create_signed_url(self, path: str, expires_in: int = SIGNED_URL_TTL_SECONDS) -> str:
        try:
            result = self.bucket.create_signed_url(path, expires_in)
            signed_url = result.get("signedURL") or result.get("signed_url")
            if not signed_url:
                raise ValueError("Storage provider did not return a signed URL.")
            return signed_url
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to create signed URL for: %s", path)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to resolve file location. Please try again.",
            ) from exc


storage_service = StorageService()
