"""
Best-effort IP -> country/city resolution using ipgeolocation.io.

Geolocation must NEVER block or fail a scan/download event. Any error here
is swallowed and (None, None) is returned instead.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "::1")


def _is_private_ip(ip: str) -> bool:
    return ip.startswith(_PRIVATE_PREFIXES) or ip.startswith("172.16.") or ip == "localhost"


def resolve_location(ip: str | None) -> tuple[str | None, str | None]:
    """Returns (country, city) for the given IP, or (None, None) if unavailable."""
    if not ip or not settings.IP_GEOLOCATION_API_KEY or _is_private_ip(ip):
        return None, None

    try:
        response = httpx.get(
            "https://api.ipgeolocation.io/ipgeo",
            params={"apiKey": settings.IP_GEOLOCATION_API_KEY, "ip": ip},
            timeout=3.0,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("country_name"), data.get("city")
    except Exception:  # noqa: BLE001
        logger.warning("Geolocation lookup failed for IP %s", ip)
        return None, None
