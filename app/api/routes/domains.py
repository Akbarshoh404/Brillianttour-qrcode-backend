from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.domain import DomainCreate, DomainListResponse, DomainResponse
from app.services import domain_service

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("", response_model=DomainListResponse)
def list_domains(db: Session = Depends(get_db)) -> DomainListResponse:
    return DomainListResponse(items=domain_service.list_domains(db))


@router.post("", response_model=DomainResponse, status_code=status.HTTP_201_CREATED)
def create_domain(payload: DomainCreate, db: Session = Depends(get_db)) -> DomainResponse:
    domain = domain_service.create_domain(db, name=payload.name, base_url=payload.base_url)
    return DomainResponse.model_validate(domain)


@router.delete("/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_domain(domain_id: int, db: Session = Depends(get_db)) -> Response:
    domain = domain_service.get_domain_or_404(db, domain_id)
    domain_service.delete_domain(db, domain)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
