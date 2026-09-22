"""Strict contracts shared by research, visual sourcing and rendering."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class ChannelProfile(BaseModel):
    """Per-channel editorial contract shared by research and rendering."""

    channel_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1, max_length=120)
    niche_id: str = Field(min_length=1)
    language: str = Field(default="tr", pattern=r"^(tr|en)$")
    brand_style: str = "documentary"
    voice_provider: str = "azure"
    caption_style: str = "word_highlight"
    color_palette: List[str] = Field(default_factory=list, max_length=12)
    banned_topics: List[str] = Field(default_factory=list, max_length=100)
    preferred_sources: List[str] = Field(default_factory=list, max_length=20)
    publishing_frequency: str = "manual_review"


class PolicySnapshot(BaseModel):
    """Immutable record of a policy/license page used by a publish decision."""

    policy_id: str = Field(min_length=1)
    title: str = Field(min_length=3)
    source_url: str = Field(min_length=8)
    retrieved_at: Optional[str] = None
    content_sha256: str = ""
    version: Optional[str] = None
    notes: str = ""

    @field_validator("source_url")
    @classmethod
    def require_https_source(cls, value: str) -> str:
        if not value.casefold().startswith("https://"):
            raise ValueError("policy snapshot source must use HTTPS")
        return value


class SceneSpec(BaseModel):
    index: int = Field(ge=0)
    narration: str = Field(min_length=12)
    duration: float = Field(gt=0, le=60)
    scene_description: str = Field(min_length=8)
    search_queries: List[str] = Field(min_length=1, max_length=8)
    beat_type: str = "body"
    visual_intent: Dict[str, Any] = Field(default_factory=dict)
    claim_ids: List[str] = Field(default_factory=list, max_length=12)
    subject: str = ""
    action: str = ""
    setting: str = ""
    lighting: str = ""
    visual_priority: str = "subject"
    must_exclude: List[str] = Field(default_factory=list, max_length=20)
    transition_intent: str = "cut"
    caption_emphasis: List[str] = Field(default_factory=list, max_length=12)
    evidence_required: bool = False

    @field_validator("narration", "scene_description")
    @classmethod
    def no_placeholder(cls, value: str) -> str:
        lowered = value.casefold()
        if "scene_description" in lowered or "placeholder" in lowered or "lorem ipsum" in lowered:
            raise ValueError("placeholder content is not publishable")
        return " ".join(value.split())


class ShortsScript(BaseModel):
    title: str = Field(min_length=4, max_length=100)
    language: str = Field(default="tr", pattern=r"^(tr|en)$")
    niche_id: str = Field(min_length=1)
    scenes: List[SceneSpec] = Field(min_length=1, max_length=24)
    research_brief: Dict[str, Any] = Field(default_factory=dict)
    full_narration: str = ""
    narrative_structure: List[str] = Field(default_factory=list, max_length=12)
    hook: str = ""
    payoff: str = ""
    loop_line: str = ""

    @model_validator(mode="after")
    def validate_timeline(self) -> "ShortsScript":
        if sum(scene.duration for scene in self.scenes) > 60.5:
            raise ValueError("Shorts timeline cannot exceed 60 seconds")
        if not self.full_narration:
            self.full_narration = " ".join(scene.narration for scene in self.scenes)
        return self


class RenderMetadata(BaseModel):
    job_id: str = Field(min_length=1)
    title: str = Field(min_length=4, max_length=100)
    language: str = Field(default="tr", pattern=r"^(tr|en)$")
    source_manifest_path: Optional[str] = None
    compliance_path: Optional[str] = None
    viewer_score: Optional[float] = Field(default=None, ge=0, le=100)
    ai_disclosure_required: bool = False
    render_settings: Dict[str, Any] = Field(default_factory=dict)
    publishing_package_path: Optional[str] = None


class ClaimAssessment(BaseModel):
    claim_id: str = Field(min_length=1)
    verdict: str = Field(pattern=r"^(supports|contradicts|unrelated|uncertain)$")
    claim_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    quote: str = Field(min_length=20)


class EvidenceRecord(BaseModel):
    """Auditable external evidence used to support one or more claims."""

    source_id: str = Field(min_length=1)
    title: str = Field(min_length=3)
    url: str = Field(min_length=8)
    source_type: str = "secondary"
    publisher: str = ""
    published_at: Optional[str] = None
    retrieved_at: Optional[str] = None
    excerpt: str = ""
    reliability: float = Field(default=0.0, ge=0, le=1)
    claim_ids: List[str] = Field(default_factory=list, max_length=20)
    retrieval_status: str = "unverified"
    content_sha256: str = ""
    assessments: List[ClaimAssessment] = Field(default_factory=list)

    @field_validator("url")
    @classmethod
    def require_https_evidence_url(cls, value: str) -> str:
        from urllib.parse import urlsplit
        parsed = urlsplit(value)
        if parsed.scheme.casefold() != "https" or not parsed.hostname:
            raise ValueError("evidence source must use an absolute HTTPS URL")
        return value

    @field_validator("content_sha256")
    @classmethod
    def require_valid_optional_hash(cls, value: str) -> str:
        import re
        if value and not re.fullmatch(r"[a-f0-9]{64}", value):
            raise ValueError("evidence content hash must be SHA-256")
        return value


class ClaimRecord(BaseModel):
    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=8)
    factual: bool = True
    status: str = "unverified"
    evidence_ids: List[str] = Field(default_factory=list, max_length=20)
    independent_source_count: int = Field(default=0, ge=0)


class PolicyDecision(BaseModel):
    action: str = "ALLOW"
    reasons: List[str] = Field(default_factory=list)
    required_review: bool = False
    ai_disclosure_required: bool = False


class ResearchBrief(BaseModel):
    topic: str = Field(min_length=2)
    niche_id: str = ""
    status: str = "evidence_insufficient"
    research_ready: bool = False
    enforce: bool = True
    claims: List[ClaimRecord] = Field(default_factory=list, max_length=40)
    evidence: List[EvidenceRecord] = Field(default_factory=list, max_length=80)
    visual_queries: List[str] = Field(default_factory=list, max_length=20)
    policy: PolicyDecision = Field(default_factory=PolicyDecision)
    source_policy: Dict[str, Any] = Field(default_factory=dict)
    retrieval_notes: List[str] = Field(default_factory=list, max_length=20)
    validation_errors: List[str] = Field(default_factory=list)
    policy_snapshots: List[PolicySnapshot] = Field(default_factory=list)

    @model_validator(mode="after")
    def derive_research_readiness(self) -> "ResearchBrief":
        from production.evidence import evaluate_evidence
        result = evaluate_evidence({
            "claims": [claim.model_dump() for claim in self.claims],
            "evidence": [source.model_dump() for source in self.evidence],
        })
        self.research_ready = result["ready"]
        self.status = "research_ready" if self.research_ready else "evidence_insufficient"
        self.claims = [ClaimRecord.model_validate(claim) for claim in result["claims"]]
        self.validation_errors = result["errors"]
        return self


class LicenseRecord(BaseModel):
    license: str = Field(min_length=1)
    source: str = Field(min_length=1)
    title: str = ""
    author: str = ""
    source_url: str = ""
    license_url: str = ""
    raw: str = ""
    safe: bool = False
    needs_attribution: bool = False
    attribution: str = ""

    @model_validator(mode="after")
    def reject_unsafe_license(self) -> "LicenseRecord":
        # Caller-controlled `safe=True` must not bypass the shared license
        # allowlist. Unknown and restrictive Creative Commons variants never
        # enter the render/manifest contract.
        from visuals.license import License, is_commercial_safe
        try:
            normalized = License(self.license)
        except ValueError:
            normalized = License.UNKNOWN
        if not is_commercial_safe(normalized):
            raise ValueError(f"license is not approved for commercial visuals: {self.license}")
        self.license = normalized.value
        self.safe = True
        return self


class VisualCandidate(BaseModel):
    uid: str = Field(min_length=3)
    source: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    url: str = Field(min_length=8)
    kind: str = "video"
    score: float = 0.0
    title: str = ""
    contributor: str = ""
    query: str = ""
    sha1: str = ""
    downloaded_at: Optional[str] = None
    source_url: str = ""
    license_url: str = ""
    attribution: str = ""
    semantic_evidence: Dict[str, Any] = Field(default_factory=dict)
    topic_match_score: float = Field(default=0.0, ge=0, le=1)
    visual_verification_score: float = Field(default=0.0, ge=0, le=1)
    matched_terms: List[str] = Field(default_factory=list, max_length=40)
    license: LicenseRecord

    @model_validator(mode="after")
    def inherit_license_provenance(self) -> "VisualCandidate":
        self.source_url = self.source_url or self.license.source_url
        self.license_url = self.license_url or self.license.license_url
        self.attribution = self.attribution or self.license.attribution
        return self


class ShotPlan(BaseModel):
    scene_index: int = Field(ge=0)
    subject: str = Field(min_length=2)
    action: str = ""
    setting: str = ""
    lighting: str = ""
    framing: str = "vertical medium shot"
    search_queries: List[str] = Field(min_length=1, max_length=8)
    must_exclude: List[str] = Field(default_factory=list, max_length=20)
    visual_priority: str = "subject"
    evidence_required: bool = False
    selected_visual: Optional[VisualCandidate] = None


class SourceManifest(BaseModel):
    version: int = 1
    generated_at: Optional[str] = None
    clips: List[VisualCandidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_assets(self) -> "SourceManifest":
        uids = [clip.uid for clip in self.clips]
        if len(uids) != len(set(uids)):
            raise ValueError("source manifest contains duplicate visual assets")
        return self
