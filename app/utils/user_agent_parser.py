"""
Lightweight, dependency-free user-agent parser.

Good enough to bucket scans into human-readable browser / OS / device
categories for internal analytics. Not intended to be exhaustive.
"""
import re
from dataclasses import dataclass


@dataclass
class ParsedUserAgent:
    browser: str
    operating_system: str
    device: str


_BROWSER_PATTERNS = [
    ("Edge", re.compile(r"Edg(?:A|iOS)?/")),
    ("Opera", re.compile(r"OPR/|Opera")),
    ("Samsung Internet", re.compile(r"SamsungBrowser/")),
    ("Chrome", re.compile(r"Chrome/")),
    ("Firefox", re.compile(r"Firefox/")),
    ("Safari", re.compile(r"Version/.*Safari/")),
    ("Internet Explorer", re.compile(r"MSIE |Trident/")),
]

_OS_PATTERNS = [
    ("iOS", re.compile(r"iPhone|iPad|iPod")),
    ("Android", re.compile(r"Android")),
    ("Windows", re.compile(r"Windows NT")),
    ("macOS", re.compile(r"Mac OS X")),
    ("Linux", re.compile(r"Linux")),
    ("Chrome OS", re.compile(r"CrOS")),
]


def parse_user_agent(user_agent: str | None) -> ParsedUserAgent:
    ua = user_agent or ""

    browser = next((name for name, pattern in _BROWSER_PATTERNS if pattern.search(ua)), "Unknown")
    operating_system = next((name for name, pattern in _OS_PATTERNS if pattern.search(ua)), "Unknown")

    if re.search(r"iPad|Tablet", ua):
        device = "Tablet"
    elif re.search(r"Mobi|iPhone|Android.*Mobile", ua):
        device = "Mobile"
    elif ua:
        device = "Desktop"
    else:
        device = "Unknown"

    return ParsedUserAgent(browser=browser, operating_system=operating_system, device=device)
