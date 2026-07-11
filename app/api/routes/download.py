from __future__ import annotations

import uuid as uuid_lib

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services import document_service
from app.services.analytics_service import record_download
from app.services.storage_service import storage_service
from app.utils.html_pages import render_error_page

router = APIRouter(tags=["download"])


@router.get("/download/{document_uuid}")
def download_and_redirect(document_uuid: uuid_lib.UUID, db: Session = Depends(get_db)):
    """Logs a download event then redirects the browser straight to the PDF."""
    document = document_service.get_public_document(db, document_uuid)

    if document is None:
        return render_error_page(
            code="404",
            heading="File not found",
            message="This document may have been deleted and is no longer available for download.",
            emoji="X",
        )

    if not document.is_active:
        return render_error_page(
            code="410",
            heading="This document is currently unavailable",
            message="The owner has temporarily disabled downloads for this file. Please check back later.",
            emoji="!",
        )

    record_download(db, document)

    signed_url = storage_service.create_signed_url(document.storage_path, bucket_name=document.storage_bucket)
    return RedirectResponse(url=signed_url, status_code=307)
