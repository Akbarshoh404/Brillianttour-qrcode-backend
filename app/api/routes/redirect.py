from __future__ import annotations

import uuid as uuid_lib

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import document_service
from app.services.analytics_service import record_scan
from app.services.storage_service import storage_service
from app.utils.html_pages import render_error_page
from app.utils.request_meta import get_client_ip

router = APIRouter(tags=["redirect"])


@router.get("/p/{document_uuid}")
def scan_and_redirect(document_uuid: uuid_lib.UUID, request: Request, db: Session = Depends(get_db)):
    """Permanent QR entry point. Logs the scan then redirects to the current PDF."""
    document = document_service.get_document_by_uuid(db, document_uuid)

    if document is None:
        return render_error_page(
            code="404",
            heading="This QR code doesn't lead anywhere",
            message="The document behind this code may have been removed or never existed.",
            emoji="X",
        )

    record_scan(
        db,
        document,
        ip=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    signed_url = storage_service.create_signed_url(document.storage_path)
    return RedirectResponse(url=signed_url, status_code=307)
