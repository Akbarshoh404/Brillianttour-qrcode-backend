from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.folder import FolderCreate, FolderListResponse, FolderResponse
from app.services import folder_service

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("", response_model=FolderListResponse)
def list_folders(db: Session = Depends(get_db)) -> FolderListResponse:
    return FolderListResponse(items=folder_service.list_folders(db))


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(payload: FolderCreate, db: Session = Depends(get_db)) -> FolderResponse:
    folder = folder_service.create_folder(db, name=payload.name)
    return folder_service.to_response(db, folder)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(folder_id: int, db: Session = Depends(get_db)) -> Response:
    folder = folder_service.get_folder_or_404(db, folder_id)
    folder_service.delete_folder(db, folder)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
