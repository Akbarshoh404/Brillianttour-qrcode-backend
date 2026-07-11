from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.download import Download
from app.models.scan import Scan
from app.schemas.scan import ScanBreakdownEntry, ScanSummaryResponse
from app.services.geolocation_service import resolve_location
from app.utils.user_agent_parser import parse_user_agent

_RECENT_SCANS_LIMIT = 10
_BREAKDOWN_LIMIT = 5


def record_scan(
    db: Session,
    document: Document,
    *,
    ip: str | None,
    user_agent: str | None,
    referrer: str | None = None,
    language: str | None = None,
    sec_ch_ua_platform: str | None = None,
    sec_ch_ua_mobile: str | None = None,
) -> Scan:
    """Persist a scan event and bump the document's rolling counters.

    Every argument here is sourced passively from the HTTP request (headers
    + IP) — nothing requires client-side JS or a permission prompt.
    """
    parsed = parse_user_agent(user_agent, sec_ch_ua_platform=sec_ch_ua_platform, sec_ch_ua_mobile=sec_ch_ua_mobile)
    geo = resolve_location(ip)

    scan = Scan(
        document_id=document.id,
        country=geo.country,
        city=geo.city,
        region=geo.region,
        isp=geo.isp,
        latitude=geo.latitude,
        longitude=geo.longitude,
        timezone=geo.timezone,
        browser=parsed.browser,
        operating_system=parsed.operating_system,
        device=parsed.device,
        user_agent=user_agent,
        ip=ip,
        referrer=referrer,
        language=language,
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


def _breakdown(db: Session, document_id: int, column) -> list[ScanBreakdownEntry]:
    label = func.coalesce(column, "Unknown").label("label")
    rows = (
        db.query(label, func.count(Scan.id).label("count"))
        .filter(Scan.document_id == document_id)
        .group_by(label)
        .order_by(func.count(Scan.id).desc())
        .limit(_BREAKDOWN_LIMIT)
        .all()
    )
    return [ScanBreakdownEntry(label=row.label, count=row.count) for row in rows]


def get_scan_summary(db: Session, document: Document) -> ScanSummaryResponse:
    """Aggregates a document's scan history into breakdowns + a recent feed
    — this is what backs the "more informative" expanded card view."""
    recent = (
        db.query(Scan).filter(Scan.document_id == document.id).order_by(Scan.created_at.desc()).limit(_RECENT_SCANS_LIMIT).all()
    )

    return ScanSummaryResponse(
        total_scans=document.total_scans,
        by_country=_breakdown(db, document.id, Scan.country),
        by_device=_breakdown(db, document.id, Scan.device),
        by_browser=_breakdown(db, document.id, Scan.browser),
        recent=list(recent),
    )
