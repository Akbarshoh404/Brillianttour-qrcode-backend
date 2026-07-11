from __future__ import annotations

import uuid as uuid_lib

from fastapi import APIRouter, Depends, Form, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.schemas.scan import ScanSummaryResponse
from app.services import document_service
from app.services.analytics_service import get_scan_summary
from app.services.qr_service import build_qr_target_url, generate_qr_png
from app.utils.file_validation import validate_pdf_upload

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile,
    title: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    contents = await validate_pdf_upload(file)
    resolved_title = (title or "").strip() or (file.filename or "Untitled document").rsplit(".", 1)[0]

    document = document_service.create_document(
        db, title=resolved_title, contents=contents, filename=file.filename or "document.pdf"
    )
    return document_service.to_response(document)


@router.get("", response_model=DocumentListResponse)
def list_documents(search: str | None = None, db: Session = Depends(get_db)) -> DocumentListResponse:
    return document_service.list_documents(db, search=search)


# NOTE: this must be registered before GET /documents/{document_uuid} —
# FastAPI/Starlette match routes in registration order, and a literal path
# segment ("trash") would otherwise be swallowed by the {document_uuid}
# path parameter.
@router.get("/trash", response_model=DocumentListResponse)
def list_trash(db: Session = Depends(get_db)) -> DocumentListResponse:
    return document_service.list_trash(db)


@router.delete("/trash/{document_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_document(document_uuid: uuid_lib.UUID, db: Session = Depends(get_db)) -> Response:
    """Immediately and irreversibly delete a document that's already in the trash."""
    document = document_service.get_document_or_404(db, document_uuid)
    document_service.hard_delete_document(db, document)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{document_uuid}", response_model=DocumentResponse)
def get_document(document_uuid: uuid_lib.UUID, db: Session = Depends(get_db)) -> DocumentResponse:
    document = document_service.get_document_or_404(db, document_uuid)
    return document_service.to_response(document)


@router.put("/{document_uuid}", response_model=DocumentResponse)
async def replace_document(
    document_uuid: uuid_lib.UUID,
    file: UploadFile,
    title: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    document = document_service.get_document_or_404(db, document_uuid)
    contents = await validate_pdf_upload(file)

    document = document_service.replace_document(
        db, document, contents=contents, filename=file.filename or "document.pdf"
    )

    if title and title.strip():
        document.title = title.strip()
        db.commit()
        db.refresh(document)

    return document_service.to_response(document)


@router.delete("/{document_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_uuid: uuid_lib.UUID, db: Session = Depends(get_db)) -> Response:
    """Moves a document to the trash. It's fully recoverable for
    TRASH_RETENTION_DAYS via POST /documents/{uuid}/restore, after which it
    is purged permanently."""
    document = document_service.get_document_or_404(db, document_uuid)
    document_service.soft_delete_document(db, document)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{document_uuid}/restore", response_model=DocumentResponse)
def restore_document(document_uuid: uuid_lib.UUID, db: Session = Depends(get_db)) -> DocumentResponse:
    document = document_service.get_document_or_404(db, document_uuid)
    document = document_service.restore_document(db, document)
    return document_service.to_response(document)


@router.post("/{document_uuid}/disable", response_model=DocumentResponse)
def disable_document(document_uuid: uuid_lib.UUID, db: Session = Depends(get_db)) -> DocumentResponse:
    """Turns a QR code off without deleting anything — e.g. a client stops
    paying. Scans/downloads are still logged as attempts; visitors just see
    an "unavailable" page instead of the PDF."""
    document = document_service.get_document_or_404(db, document_uuid)
    document = document_service.set_active_status(db, document, is_active=False)
    return document_service.to_response(document)


@router.post("/{document_uuid}/enable", response_model=DocumentResponse)
def enable_document(document_uuid: uuid_lib.UUID, db: Session = Depends(get_db)) -> DocumentResponse:
    document = document_service.get_document_or_404(db, document_uuid)
    document = document_service.set_active_status(db, document, is_active=True)
    return document_service.to_response(document)


@router.get("/{document_uuid}/scans/summary", response_model=ScanSummaryResponse)
def get_document_scan_summary(document_uuid: uuid_lib.UUID, db: Session = Depends(get_db)) -> ScanSummaryResponse:
    document = document_service.get_document_or_404(db, document_uuid)
    return get_scan_summary(db, document)


@router.get("/{document_uuid}/qr")
def get_document_qr(document_uuid: uuid_lib.UUID, db: Session = Depends(get_db)) -> StreamingResponse:
    document = document_service.get_document_or_404(db, document_uuid)
    target_url = build_qr_target_url(document.uuid)
    png_bytes = generate_qr_png(target_url)

    return StreamingResponse(
        iter([png_bytes]),
        media_type="image/png",
        headers={
            "Content-Disposition": f'inline; filename="{document.uuid}-qr.png"',
            "Cache-Control": "no-store",
        },
    )
