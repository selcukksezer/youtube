"""Channel and niche production profiles used by the policy-aware pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class ChannelProfile:
    """Serializable channel contract shared by TR/EN channel packages."""

    channel_id: str = "default"
    niche_id: str = ""
    language: str = "tr"
    style_id: str = "documentary_short"
    voice_id: str = ""
    palette: List[str] = field(default_factory=lambda: ["#111827", "#F8FAFC", "#F59E0B"])
    caption_preset: str = "high_contrast_retention"
    allowed_providers: List[str] = field(default_factory=lambda: [
        "pexels", "pixabay", "coverr", "openverse", "wikimedia", "nasa", "archive_org",
    ])
    max_daily_outputs: int = 3
    forbidden_topics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def channel_profile(channel_id: str = "default", *, niche_id: str = "", language: str = "tr", **overrides: Any) -> ChannelProfile:
    """Build a deterministic profile without requiring a database migration."""
    values = {
        "channel_id": channel_id or "default",
        "niche_id": niche_id or "",
        "language": (language or "tr").lower(),
    }
    values.update({k: v for k, v in overrides.items() if v is not None})
    return ChannelProfile(**values)

