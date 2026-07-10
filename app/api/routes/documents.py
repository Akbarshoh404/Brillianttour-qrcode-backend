from __future__ import annotations

import uuid as uuid_lib

from fastapi import APIRouter, Depends, Form, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.services import document_service
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
    document = document_service.get_document_or_404(db, document_uuid)
    document_service.delete_document(db, document)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
