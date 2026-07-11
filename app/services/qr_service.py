"""
Generates QR codes on demand, in memory only.

Per spec: QR images are never persisted anywhere (not in the database, not
on disk). Every request regenerates the PNG from the permanent
{PUBLIC_BASE_URL}/p/{uuid} link, so there is nothing to invalidate when a
PDF is replaced or the domain changes.
"""
from __future__ import annotations

import io
import uuid as uuid_lib

import qrcode
from qrcode.image.pil import PilImage

from app.config import settings


def build_qr_target_url(document_uuid: uuid_lib.UUID, base_url: str | None = None) -> str:
    """The permanent, public URL encoded into the QR code.

    `base_url` lets a document use a different public domain than the
    globally configured default (see the domains feature) — still never
    hardcoded, just resolved per-document instead of from a single env var.
    """
    resolved = (base_url or settings.PUBLIC_BASE_URL).rstrip("/")
    return f"{resolved}/p/{document_uuid}"


def generate_qr_png(data: str) -> bytes:
    """Render `data` as a PNG QR code and return the raw bytes."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        # 2 modules is the smallest quiet zone that keeps the code reliably
        # scannable while avoiding the large white margin the default (4)
        # produces.
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    image: PilImage = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
