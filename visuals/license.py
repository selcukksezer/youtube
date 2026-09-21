"""License model for sourced visuals. Only commercial-safe, attribution-friendly licenses pass."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional


class License(str, Enum):
    CC0 = "cc0"
    PUBLIC_DOMAIN = "public_domain"
    CC_BY = "cc_by"
    PEXELS = "pexels"            # platform license, commercial OK, no attribution required
    PIXABAY = "pixabay"          # platform license, commercial OK
    COVERR = "coverr"            # platform license, commercial OK
    MIXKIT = "mixkit"            # platform license, commercial OK
    AI_GENERATED = "ai_generated"  # provider ToS; disclose in description
    CC_BY_SA = "cc_by_sa"        # share-alike: NOT used (derivative must be SA)
    CC_NC = "cc_nc"              # non-commercial: NOT used
    CC_ND = "cc_nd"              # no-derivatives: NOT used
    UNKNOWN = "unknown"


COMMERCIAL_SAFE = {
    License.CC0,
    License.PUBLIC_DOMAIN,
    License.CC_BY,
    License.PEXELS,
    License.PIXABAY,
    License.COVERR,
    License.MIXKIT,
    License.AI_GENERATED,
}

ATTRIBUTION_REQUIRED = {License.CC_BY, License.AI_GENERATED}


@dataclass
class LicenseInfo:
    license: License
    source: str                      # provider key (pexels, wikimedia, nasa, ...)
    title: str = ""
    author: str = ""
    source_url: str = ""
    license_url: str = ""
    raw: str = ""                    # provider's raw license string for audit

    @property
    def safe(self) -> bool:
        return is_commercial_safe(self.license)

    @property
    def needs_attribution(self) -> bool:
        return self.license in ATTRIBUTION_REQUIRED

    def to_dict(self) -> dict:
        d = asdict(self)
        d["license"] = self.license.value
        d["safe"] = self.safe
        d["needs_attribution"] = self.needs_attribution
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "LicenseInfo":
        lic = d.get("license", "unknown")
        try:
            lic_enum = License(lic)
        except ValueError:
            lic_enum = License.UNKNOWN
        return cls(
            license=lic_enum,
            source=str(d.get("source", "")),
            title=str(d.get("title", "")),
            author=str(d.get("author", "")),
            source_url=str(d.get("source_url", "")),
            license_url=str(d.get("license_url", "")),
            raw=str(d.get("raw", "")),
        )


def is_commercial_safe(lic: License) -> bool:
    return lic in COMMERCIAL_SAFE


_CC_PATTERNS = [
    # order matters: restrictive flags first
    (re.compile(r"\bnc\b|non[- ]?commercial", re.I), License.CC_NC),
    (re.compile(r"\bnd\b|no[- ]?deriv", re.I), License.CC_ND),
    (re.compile(r"\bsa\b|share[- ]?alike", re.I), License.CC_BY_SA),
    (re.compile(r"cc[- ]?0|zero|cc0", re.I), License.CC0),
    (re.compile(r"public\s*domain|\bpd\b|pdm|publicdomain|no known copyright|us government work", re.I), License.PUBLIC_DOMAIN),
    (re.compile(r"cc[- ]?by\b|attribution|licenses/by/", re.I), License.CC_BY),
]


def parse_cc_license(raw: str) -> License:
    """Map a Creative Commons / Wikimedia / Openverse license label or URL to License."""
    text = (raw or "").strip()
    if not text:
        return License.UNKNOWN
    low = text.lower()
    # URL forms are the most reliable
    if "publicdomain/zero" in low:
        return License.CC0
    if "publicdomain/mark" in low or "publicdomain" in low:
        return License.PUBLIC_DOMAIN
    m = re.search(r"licenses/(by(?:-[a-z]+)*)/", low)
    if m:
        parts = set(m.group(1).split("-"))
        if "nc" in parts:
            return License.CC_NC
        if "nd" in parts:
            return License.CC_ND
        if "sa" in parts:
            return License.CC_BY_SA
        return License.CC_BY
    for pattern, lic in _CC_PATTERNS:
        if pattern.search(low):
            return lic
    return License.UNKNOWN


def attribution_line(info: LicenseInfo) -> Optional[str]:
    """Human-readable credit line; None when the license needs no attribution."""
    if info.license in (License.PEXELS, License.PIXABAY, License.COVERR, License.MIXKIT):
        return None
    label = {
        License.CC0: "CC0",
        License.PUBLIC_DOMAIN: "Public Domain",
        License.CC_BY: "CC BY",
        License.AI_GENERATED: "AI-generated",
    }.get(info.license)
    if not label:
        return None
    if info.license == License.AI_GENERATED:
        src = info.source.replace("_", " ").title() or "AI"
        model = info.title or "video"
        return f"AI video via {src} ({model})".strip()
    if info.license != License.CC_BY and not info.author:
        # CC0 / PD: attribution optional; still credit source politely when title known
        if not info.title:
            return None
    title = info.title or "Untitled"
    author = f" — {info.author}" if info.author else ""
    url = f" {info.source_url}" if info.source_url else ""
    src = info.source.replace("_", " ").title()
    return f"\"{title}\"{author} via {src} ({label}){url}".strip()
