"""
services/bgm_security.py — Background Music File Security & Validation Guard.

Adapted and evolved from reference_repos2/MoneyPrinterTurbo (app/services/bgm.py).
Enforces:
1. Max upload limit (30MB) preventing disk exhaustion.
2. Extension whitelist (.mp3, .m4a, .aac, .wav, .flac, .ogg, .opus, .wma).
3. Rejection of Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9).
4. Rejection of dangerous Unicode control codes (C0, C1, Right-to-Left Override U+202E).
5. Centralized volume & BGM engagement check.
"""

from __future__ import annotations

import os
from typing import Optional


MAX_BGM_UPLOAD_BYTES = 30 * 1024 * 1024  # 30 MB

SUPPORTED_BGM_EXTENSIONS = frozenset({
    ".mp3",
    ".m4a",
    ".aac",
    ".wav",
    ".flac",
    ".ogg",
    ".opus",
    ".wma",
})

_WINDOWS_RESERVED_FILENAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)}
    | {f"{prefix}{number}" for prefix in ("COM", "LPT") for number in ("¹", "²", "³")}
)

_UNSAFE_FILENAME_CHARACTERS = frozenset(
    chr(code)
    for code in (
        *range(0x00, 0x20),      # C0 controls
        *range(0x7F, 0xA0),      # C1 controls (U+0085 fake newline)
        0x200E, 0x200F,          # LTR / RTL marks
        0x2028, 0x2029,          # Line / Paragraph separators
        *range(0x202A, 0x202F),  # Bidi embedding / overrides (U+202E)
        *range(0x2066, 0x206A),  # Bidi isolates
    )
)


class BgmSecurityError(ValueError):
    """Raised when an uploaded audio file violates security or format standards."""


def should_use_bgm(bgm_type: Optional[str], bgm_volume: Optional[float]) -> bool:
    """
    Returns True if BGM processing should proceed.
    Skips mixing and resource allocation if volume is <= 0 or type is 'none'/empty.
    """
    if not bgm_type or str(bgm_type).strip().lower() in ("none", "muted", "disabled"):
        return False
    if bgm_volume is None or float(bgm_volume) <= 0.001:
        return False
    return True


def validate_bgm_filename(filename: str) -> str:
    """
    Validates audio filename against path traversal, Windows device names,
    Unicode spoofing, and disallowed extensions.
    """
    if not isinstance(filename, str) or not filename.strip():
        raise BgmSecurityError("Filename cannot be empty.")

    clean_name = os.path.basename(filename.strip())

    # Path traversal check
    if ".." in filename or "/" in filename or "\\" in filename:
        raise BgmSecurityError("Path traversal characters are strictly forbidden.")

    # Null bytes
    if "\x00" in clean_name:
        raise BgmSecurityError("Null bytes detected in filename.")

    # Unicode spoofing / Bidi overrides
    if any(ch in _UNSAFE_FILENAME_CHARACTERS for ch in clean_name):
        raise BgmSecurityError("Disallowed control or bidirectional override characters in filename.")

    # Extension check
    stem, ext = os.path.splitext(clean_name)
    ext_lower = ext.lower()
    if ext_lower not in SUPPORTED_BGM_EXTENSIONS:
        raise BgmSecurityError(
            f"Unsupported audio format '{ext}'. Must be one of: {', '.join(sorted(SUPPORTED_BGM_EXTENSIONS))}"
        )

    # Windows reserved names
    if stem.upper() in _WINDOWS_RESERVED_FILENAMES:
        raise BgmSecurityError(f"'{stem}' is a Windows reserved device name.")

    return clean_name


def validate_bgm_file(filename: str, file_size: Optional[int] = None) -> str:
    """
    Full validation of BGM filename and payload size.
    """
    clean_name = validate_bgm_filename(filename)

    if file_size is not None and file_size > MAX_BGM_UPLOAD_BYTES:
        max_mb = MAX_BGM_UPLOAD_BYTES / (1024 * 1024)
        raise BgmSecurityError(f"Audio file size exceeds maximum permitted limit ({max_mb:.0f}MB).")

    return clean_name
