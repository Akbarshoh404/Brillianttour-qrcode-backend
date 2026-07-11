from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.domain import Domain
from app.schemas.domain import DomainResponse


def _default_domain_response() -> DomainResponse:
    """The implicit domain every document falls back to — whatever
    PUBLIC_BASE_URL is set to in the environment. Not a database row."""
    return DomainResponse(
        id=None,
        name="Default",
        base_url=settings.PUBLIC_BASE_URL.rstrip("/"),
        created_at=None,
        is_default=True,
    )


def list_domains(db: Session) -> list[DomainResponse]:
    domains = db.query(Domain).order_by(Domain.created_at.asc()).all()
    return [_default_domain_response()] + [DomainResponse.model_validate(d) for d in domains]


def create_domain(db: Session, *, name: str, base_url: str) -> Domain:
    normalized = base_url.strip().rstrip("/")
    if not normalized.startswith("http://") and not normalized.startswith("https://"):
        normalized = f"https://{normalized}"

    existing = db.query(Domain).filter(Domain.base_url == normalized).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That domain has already been added.")

    domain = Domain(name=name.strip() or normalized, base_url=normalized)
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


def get_domain_or_404(db: Session, domain_id: int) -> Domain:
    domain = db.query(Domain).filter(Domain.id == domain_id).first()
    if domain is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found.")
    return domain


def delete_domain(db: Session, domain: Domain) -> None:
    """Deleting a domain doesn't touch its documents — the FK is ON DELETE
    SET NULL, so they just fall back to the default domain."""
    db.delete(domain)
    db.commit()


def resolve_base_url(domain: Domain | None) -> str:
    if domain is None:
        return settings.PUBLIC_BASE_URL.rstrip("/")
    return domain.base_url.rstrip("/")
