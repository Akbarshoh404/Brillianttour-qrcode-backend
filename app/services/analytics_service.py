from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.download import Download
from app.models.scan import Scan
from app.services.geolocation_service import resolve_location
from app.utils.user_agent_parser import parse_user_agent


def record_scan(db: Session, document: Document, *, ip: str | None, user_agent: str | None) -> Scan:
    """Persist a scan event and bump the document's rolling counters."""
    parsed = parse_user_agent(user_agent)
    country, city = resolve_location(ip)

    scan = Scan(
        document_id=document.id,
        country=country,
        city=city,
        browser=parsed.browser,
        operating_system=parsed.operating_system,
        device=parsed.device,
        user_agent=user_agent,
        ip=ip,
    )
    db.add(scan)

    document.total_scans += 1
    document.last_scan = datetime.now(timezone.utc)

    db.commit()
    db.refresh(scan)
    return scan


def record_download(db: Session, document: Document) -> Download:
    """Persist a download event and bump the document's rolling counters."""
    download = Download(document_id=document.id)
    db.add(download)

    document.total_downloads += 1
    document.last_download = datetime.now(timezone.utc)

    db.commit()
    db.refresh(download)
    return download
