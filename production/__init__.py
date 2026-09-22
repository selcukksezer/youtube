"""Production-grade, policy-aware building blocks for Shorts rendering."""

from .schemas import (
    ClaimRecord,
    ChannelProfile,
    EvidenceRecord,
    PolicyDecision,
    PolicySnapshot,
    RenderMetadata,
    ResearchBrief,
    SceneSpec,
    LicenseRecord,
    VisualCandidate,
    ShotPlan,
    SourceManifest,
    ShortsScript,
)
from .stock_fetcher import AsyncStockFetcher
from .video_engine import VideoEngine
from .profiles import ChannelProfile as RuntimeChannelProfile, channel_profile
from .quality import validate_script_quality, build_policy_snapshot
from .package import write_delivery_package
from .evidence import evaluate_evidence, publisher_group, domain_group, text_hash

__all__ = [
    "SceneSpec", "ShortsScript", "RenderMetadata", "EvidenceRecord",
    "ClaimRecord", "ChannelProfile", "PolicyDecision", "PolicySnapshot", "ResearchBrief", "AsyncStockFetcher",
    "LicenseRecord", "VisualCandidate", "ShotPlan", "SourceManifest",
    "VideoEngine",
    "ChannelProfile", "RuntimeChannelProfile", "channel_profile", "validate_script_quality",
    "build_policy_snapshot", "write_delivery_package",
    "evaluate_evidence", "publisher_group", "domain_group", "text_hash",
]
