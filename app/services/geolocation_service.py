"""
Best-effort IP -> geolocation resolution using ipgeolocation.io.

This is passive, permission-less tracking: it works purely off the IP
address already present on every incoming HTTP request, the same way
server access logs and virtually every analytics tool on the web work.
Nothing here requests (or tries to work around) a browser permission
prompt — there is no way to get precise GPS-level location without one,
and this deliberately does not attempt to.

Geolocation must NEVER block or fail a scan/download event: any error here
is swallowed and an empty result is returned instead.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_PRIVATE_PREFIXES = ("127.", "10.", "192.168.", "::1")


@dataclass
class GeoLocation:
    country: str | None = None
    city: str | None = None
    region: str | None = None
    isp: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None


def _is_private_ip(ip: str) -> bool:
    return ip.startswith(_PRIVATE_PREFIXES) or ip.startswith("172.16.") or ip == "localhost"


def resolve_location(ip: str | None) -> GeoLocation:
    """Best-effort geo-IP lookup. Returns an all-None GeoLocation on any failure."""
    if not ip or not settings.IP_GEOLOCATION_API_KEY or _is_private_ip(ip):
        return GeoLocation()

    try:
        response = httpx.get(
            "https://api.ipgeolocation.io/ipgeo",
            params={"apiKey": settings.IP_GEOLOCATION_API_KEY, "ip": ip},
            timeout=3.0,
        )
        response.raise_for_status()
        data = response.json()

        latitude = _to_float(data.get("latitude"))
        longitude = _to_float(data.get("longitude"))

        return GeoLocation(
            country=data.get("country_name"),
            city=data.get("city"),
            region=data.get("state_prov"),
            isp=data.get("isp"),
            latitude=latitude,
            longitude=longitude,
            timezone=(data.get("time_zone") or {}).get("name"),
        )
    except Exception:  # noqa: BLE001
        logger.warning("Geolocation lookup failed for IP %s", ip)
        return GeoLocation()


def _to_float(value: object) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None
