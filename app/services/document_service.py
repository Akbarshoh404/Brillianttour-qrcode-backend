from __future__ import annotations

import secrets
import uuid as uuid_lib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.document import Document
from app.schemas.document import DocumentListResponse, DocumentResponse
from app.services.qr_service import build_qr_target_url
from app.services.storage_service import storage_service


def _new_storage_path(document_uuid: uuid_lib.UUID, filename: str) -> str:
    """A unique, non-guessable path for a single PDF revision.

    Replacing a PDF writes to a brand new path rather than overwriting the
    old one in place, so a half-finished upload can never corrupt the file
    a live QR code currently points to.
    """
    suffix = Path(filename).suffix or ".pdf"
    return f"{document_uuid}/{secrets.token_hex(8)}{suffix}"


def to_response(document: Document) -> DocumentResponse:
    base_url = settings.PUBLIC_BASE_URL.rstrip("/")
    purge_at = None
    if document.deleted_at is not None:
        purge_at = document.deleted_at + timedelta(days=settings.TRASH_RETENTION_DAYS)

    return DocumentResponse(
        id=document.id,
        uuid=document.uuid,
        title=document.title,
        file_size=document.file_size,
        created_at=document.created_at,
        updated_at=document.updated_at,
        total_scans=document.total_scans,
        total_downloads=document.total_downloads,
        last_scan=document.last_scan,
        last_download=document.last_download,
        is_active=document.is_active,
        deleted_at=document.deleted_at,
        purge_at=purge_at,
        qr_url=f"{base_url}/documents/{document.uuid}/qr",
        view_url=storage_service.create_signed_url(document.storage_path),
        download_url=f"{base_url}/download/{document.uuid}",
        qr_link=build_qr_target_url(document.uuid),
    )


def create_document(db: Session, *, title: str, contents: bytes, filename: str) -> Document:
    document_uuid = uuid_lib.uuid4()
    storage_path = _new_storage_path(document_uuid, filename)

    storage_service.upload(storage_path, contents)

    document = Document(
        uuid=document_uuid,
        title=title,
        storage_path=storage_path,
        file_size=len(contents),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_documents(db: Session, *, search: str | None = None) -> DocumentListResponse:
    """Active + disabled documents — excludes anything in the trash."""
    purge_expired_trash(db)

    documents = db.query(Document).filter(Document.deleted_at.is_(None)).order_by(Document.created_at.desc()).all()

    if search:
        needle = search.strip().lower()
        documents = [d for d in documents if needle in d.title.lower() or needle in str(d.uuid).lower()]

    total_size = (
        db.query(func.coalesce(func.sum(Document.file_size), 0)).filter(Document.deleted_at.is_(None)).scalar() or 0
    )

    return DocumentListResponse(
        items=[to_response(d) for d in documents],
        total=len(documents),
        storage_used_bytes=int(total_size),
    )


def list_trash(db: Session) -> DocumentListResponse:
    purge_expired_trash(db)

    documents = db.query(Document).filter(Document.deleted_at.is_not(None)).order_by(Document.deleted_at.desc()).all()

    return DocumentListResponse(
        items=[to_response(d) for d in documents],
        total=len(documents),
        storage_used_bytes=0,
    )


def get_document_by_uuid(db: Session, document_uuid: uuid_lib.UUID) -> Document | None:
    return db.query(Document).filter(Document.uuid == document_uuid).first()


def get_public_document(db: Session, document_uuid: uuid_lib.UUID) -> Document | None:
    """Lookup used by /p/{uuid} and /download/{uuid}. Trashed documents are
    treated as gone entirely; disabled documents are still returned so the
    caller can show a distinct "unavailable" page rather than a 404.
    """
    return db.query(Document).filter(Document.uuid == document_uuid, Document.deleted_at.is_(None)).first()


def get_document_or_404(db: Session, document_uuid: uuid_lib.UUID) -> Document:
    document = get_document_by_uuid(db, document_uuid)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


def replace_document(db: Session, document: Document, *, contents: bytes, filename: str) -> Document:
    """Replace the underlying PDF while keeping uuid (and therefore the QR) identical."""
    old_storage_path = document.storage_path
    new_storage_path = _new_storage_path(document.uuid, filename)

    storage_service.upload(new_storage_path, contents)

    document.storage_path = new_storage_path
    document.file_size = len(contents)
    db.commit()
    db.refresh(document)

    storage_service.delete(old_storage_path)
    return document


def set_active_status(db: Session, document: Document, *, is_active: bool) -> Document:
    """Turn a QR code off/on without touching its file or history — e.g. to
    suspend access for a client who hasn't paid, without deleting anything.
    """
    document.is_active = is_active
    db.commit()
    db.refresh(document)
    return document


def soft_delete_document(db: Session, document: Document) -> Document:
    """Move a document to the trash. Fully reversible via restore_document
    until it's purged (see purge_expired_trash)."""
    document.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(document)
    return document


def restore_document(db: Session, document: Document) -> Document:
    document.deleted_at = None
    db.commit()
    db.refresh(document)
    return document


def hard_delete_document(db: Session, document: Document) -> None:
    """Irreversibly delete the database row and the storage object."""
    storage_path = document.storage_path
    db.delete(document)
    db.commit()
    storage_service.delete(storage_path)


def purge_expired_trash(db: Session) -> int:
    """Permanently deletes anything that's been in the trash longer than
    TRASH_RETENTION_DAYS. Called opportunistically from list_documents/
    list_trash rather than on a background scheduler, to avoid needing a
    long-running worker process for what is a very low-frequency cleanup.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.TRASH_RETENTION_DAYS)
    expired = db.query(Document).filter(Document.deleted_at.is_not(None), Document.deleted_at < cutoff).all()

    for document in expired:
        hard_delete_document(db, document)

    return len(expired)
