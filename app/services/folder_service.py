from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.folder import Folder
from app.schemas.folder import FolderResponse
from app.services import document_service
from app.services.storage_service import storage_service
from app.utils.slug import unique_bucket_name


def to_response(db: Session, folder: Folder) -> FolderResponse:
    active_count = (
        db.query(func.count(Document.id))
        .filter(Document.folder_id == folder.id, Document.deleted_at.is_(None))
        .scalar()
        or 0
    )
    return FolderResponse(
        id=folder.id,
        name=folder.name,
        created_at=folder.created_at,
        document_count=int(active_count),
    )


def list_folders(db: Session) -> list[FolderResponse]:
    folders = db.query(Folder).order_by(Folder.name.asc()).all()
    return [to_response(db, f) for f in folders]


def create_folder(db: Session, *, name: str) -> Folder:
    name = name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Folder name is required.")

    bucket_name = unique_bucket_name(name)
    storage_service.create_bucket(bucket_name)

    folder = Folder(name=name, storage_bucket=bucket_name)
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def get_folder_or_404(db: Session, folder_id: int) -> Folder:
    folder = db.query(Folder).filter(Folder.id == folder_id).first()
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found.")
    return folder


def delete_folder(db: Session, folder: Folder, *, force: bool = False) -> None:
    """Refuses to delete a folder that still has documents in it (including
    trashed ones — their files still live in this folder's bucket, and
    deleting it out from under them would break trash restore) — unless
    `force` is set, in which case those documents are permanently deleted
    right along with the folder."""
    documents = db.query(Document).filter(Document.folder_id == folder.id).all()
    if documents and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This folder still has documents in it (including trash). Move or permanently delete them first.",
        )

    for document in documents:
        document_service.hard_delete_document(db, document)

    bucket_name = folder.storage_bucket
    db.delete(folder)
    db.commit()
    storage_service.delete_bucket(bucket_name)
