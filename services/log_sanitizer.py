"""Strip secrets before they reach SSE, logs, or the database."""
from __future__ import annotations

import re
from typing import Any

_ASSIGNED = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|authorization|bearer)\b\s*[:=]\s*\S+"
)
_BEARER = re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9_\-\.]{8,}")
_BARE = re.compile(r"\b(?:sk-|AIza|ya29\.)[A-Za-z0-9_\-]{8,}")
_SENSITIVE_KEY_SUBSTRINGS = (
    "api_key", "apikey", "token", "secret", "password", "auth", "credential"
)


def sanitize_log(text: str) -> str:
    cleaned = _ASSIGNED.sub(lambda m: f"{m.group(1)}=[REDACTED]", str(text))
    cleaned = _BEARER.sub(r"\1[REDACTED]", cleaned)
    return _BARE.sub("[REDACTED]", cleaned)


def sanitize_payload(data: Any) -> Any:
    if isinstance(data, str):
        return sanitize_log(data)
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            k_lower = str(key).lower()
            if any(s in k_lower for s in _SENSITIVE_KEY_SUBSTRINGS) and isinstance(value, (str, bytes, int)):
                result[key] = "[REDACTED]"
            else:
                result[key] = sanitize_payload(value)
        return result
    if isinstance(data, list):
        return [sanitize_payload(item) for item in data]
    return data
