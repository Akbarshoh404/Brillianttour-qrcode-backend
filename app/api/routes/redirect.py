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
from app.utils.request_meta import get_client_ip, get_primary_language

router = APIRouter(tags=["redirect"])


@router.get("/p/{document_uuid}")
def scan_and_redirect(document_uuid: uuid_lib.UUID, request: Request, db: Session = Depends(get_db)):
    """Permanent QR entry point. Logs the scan then redirects to the current PDF."""
    document = document_service.get_public_document(db, document_uuid)

    if document is None:
        return render_error_page(
            code="404",
            heading="This QR code doesn't lead anywhere",
            message="The document behind this code may have been removed or never existed.",
            emoji="X",
        )

    # Log the scan regardless of active status — an attempted scan of a
    # disabled document is still useful signal (e.g. "12 people tried to
    # open this expired brochure").
    record_scan(
        db,
        document,
        ip=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        referrer=request.headers.get("referer"),
        language=get_primary_language(request),
        sec_ch_ua_platform=request.headers.get("sec-ch-ua-platform"),
        sec_ch_ua_mobile=request.headers.get("sec-ch-ua-mobile"),
    )

    if not document.is_active:
        return render_error_page(
            code="410",
            heading="This document is currently unavailable",
            message="The owner has temporarily disabled this QR code. Please check back later.",
            emoji="!",
        )

    signed_url = storage_service.create_signed_url(document.storage_path)
    return RedirectResponse(url=signed_url, status_code=307)
