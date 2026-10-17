# -*- coding: utf-8 -*-
"""
Pipeline Stage Specifications, Execution Records, and Reference PipelineState Adapter.
Extracted from server_core/pipeline_state_machine.py for modularity.
"""
from __future__ import annotations

import enum
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class PipelineStage(str, enum.Enum):
    """The 10 deterministic stages defined in Section 1.3 of plan.md."""
    STAGE_1_VALIDATION = "STAGE_1_VALIDATION"
    STAGE_2_HOOK_NARRATIVE = "STAGE_2_HOOK_NARRATIVE"
    STAGE_3_DIRECTOR_PLAN = "STAGE_3_DIRECTOR_PLAN"
    STAGE_4_ORIGINALITY_GATE = "STAGE_4_ORIGINALITY_GATE"
    STAGE_5_ASSET_INGESTION = "STAGE_5_ASSET_INGESTION"
    STAGE_6_TTS_SYNC = "STAGE_6_TTS_SYNC"
    STAGE_7_AUDIO_MASTERING = "STAGE_7_AUDIO_MASTERING"
    STAGE_8_SUBTITLE_COMPILE = "STAGE_8_SUBTITLE_COMPILE"
    STAGE_9_FFMPEG_RENDER = "STAGE_9_FFMPEG_RENDER"
    STAGE_10_PACKAGING = "STAGE_10_PACKAGING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class StageMetadata:
    order: int
    name_tr: str
    min_pct: float
    max_pct: float
    description: str


STAGE_SPECS: Dict[PipelineStage, StageMetadata] = {
    PipelineStage.STAGE_1_VALIDATION: StageMetadata(
        order=1,
        name_tr="İstek Kabulü ve Doğrulama",
        min_pct=0.0,
        max_pct=5.0,
        description="Girdi parametreleri, niş şablonu, donanım ve seslendirmen ayarları doğrulanır.",
    ),
    PipelineStage.STAGE_2_HOOK_NARRATIVE: StageMetadata(
        order=2,
        name_tr="Kanca ve Anlatı Üretimi",
        min_pct=5.0,
        max_pct=15.0,
        description="Psikolojik kanca (retention hook) ve izleyici tutundurma açılışı kurgulanır.",
    ),
    PipelineStage.STAGE_3_DIRECTOR_PLAN: StageMetadata(
        order=3,
        name_tr="Senaryo Derleme (DirectorPlan)",
        min_pct=15.0,
        max_pct=25.0,
        description="Timeline oluşturulur, görsel niyetler (visual intent) ve BPM ritim ipuçları derlenir.",
    ),
    PipelineStage.STAGE_4_ORIGINALITY_GATE: StageMetadata(
        order=4,
        name_tr="Özgünlük Kontrolü (Madde 120)",
        min_pct=25.0,
        max_pct=30.0,
        description="Çapraz senaryo intihal ve kelime benzerlik kontrolü çalıştırılır.",
    ),
    PipelineStage.STAGE_5_ASSET_INGESTION: StageMetadata(
        order=5,
        name_tr="Varlık Edinimi (Asset Ingestion)",
        min_pct=30.0,
        max_pct=55.0,
        description="Pexels, Pixabay, AI Video ve prosedürel stok klipler paralel indirilir; lisans defterine işlenir.",
    ),
    PipelineStage.STAGE_6_TTS_SYNC: StageMetadata(
        order=6,
        name_tr="Seslendirme ve Zamanlama (TTS Sync)",
        min_pct=55.0,
        max_pct=65.0,
        description="Edge/ElevenLabs seslendirme sentezlenir, kelime düzeyinde zaman damgaları çıkarılır.",
    ),
    PipelineStage.STAGE_7_AUDIO_MASTERING: StageMetadata(
        order=7,
        name_tr="Akustik Tasarım ve Miksaj",
        min_pct=65.0,
        max_pct=75.0,
        description="BGM sidechain ducking (-18dB), ses sıcaklığı EQ ve EBU R128 (-14 LUFS) tek geçişte işlenir.",
    ),
    PipelineStage.STAGE_8_SUBTITLE_COMPILE: StageMetadata(
        order=8,
        name_tr="Kinetik Altyazı Derleme",
        min_pct=75.0,
        max_pct=82.0,
        description="Vektörel ASS altyazı dosyası, aktif kelime zıplama animasyonu ve güvenli alan sınırları derlenir.",
    ),
    PipelineStage.STAGE_9_FFMPEG_RENDER: StageMetadata(
        order=9,
        name_tr="FFmpeg FilterComplex Render",
        min_pct=82.0,
        max_pct=95.0,
        description="Tek geçişte donanım ivmeli (NVENC/QSV/libx264) video filtre grafiği render edilir.",
    ),
    PipelineStage.STAGE_10_PACKAGING: StageMetadata(
        order=10,
        name_tr="Paketleme ve Dağıtım",
        min_pct=95.0,
        max_pct=100.0,
        description="Lisans künyesi (visual_credits.json), yayın paketi ve SEO meta verileri arşivlenir.",
    ),
    PipelineStage.COMPLETED: StageMetadata(
        order=11,
        name_tr="Tamamlandı",
        min_pct=100.0,
        max_pct=100.0,
        description="Tüm üretim aşamaları sıfır hatayla başarıyla tamamlandı.",
    ),
    PipelineStage.FAILED: StageMetadata(
        order=99,
        name_tr="Hata / İptal",
        min_pct=0.0,
        max_pct=100.0,
        description="Üretim aşamalarından birinde hata meydana geldi veya işlem iptal edildi.",
    ),
}


@dataclass
class StageExecutionRecord:
    stage: PipelineStage
    order: int
    name_tr: str
    started_at: float
    ended_at: Optional[float] = None
    duration_sec: float = 0.0
    start_pct: float = 0.0
    end_pct: float = 0.0
    message: str = ""
    status: str = "running"


# ─── ITEM P7: Reference Repo Compatibility Adapter (youtube-shorts-pipeline) ─

REFERENCE_PIPELINE_STAGES = [
    "research", "draft", "broll", "voiceover", "whisper",
    "captions", "music", "assemble", "thumbnail", "upload",
]


class PipelineState:
    """
    Direct implementation of youtube-shorts-pipeline/verticals/state.py PipelineState.
    Elevated with resilience: checks file sizes and existence on reusable().
    """

    def __init__(self, draft: Optional[Dict[str, Any]] = None):
        self.draft = draft if isinstance(draft, dict) else {}
        if "_pipeline_state" not in self.draft:
            self.draft["_pipeline_state"] = {}

    @property
    def state(self) -> Dict[str, Any]:
        return self.draft["_pipeline_state"]

    def is_done(self, stage: str) -> bool:
        """Check if a stage completed successfully."""
        entry = self.state.get(stage, {})
        return entry.get("status") == "done"

    def is_failed(self, stage: str) -> bool:
        entry = self.state.get(stage, {})
        return entry.get("status") == "failed"

    def complete_stage(
        self,
        stage: str,
        artifacts: Optional[Dict[str, Any]] = None,
        files: Optional[List[str]] = None,
    ) -> None:
        """Mark a stage as completed with optional artifact metadata and files."""
        self.state[stage] = {
            "status": "done",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if artifacts:
            self.state[stage]["artifacts"] = artifacts
        if files:
            self.state[stage]["files"] = [p for p in files if p]

    def fail_stage(self, stage: str, error: str = "") -> None:
        """Mark a stage as failed."""
        self.state[stage] = {
            "status": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }

    def get_artifact(self, stage: str, key: str, default: Any = None) -> Any:
        """Get an artifact value from a completed stage."""
        entry = self.state.get(stage, {})
        artifacts = entry.get("artifacts", {})
        return artifacts.get(key, default) if isinstance(artifacts, dict) else default

    def reset(self) -> None:
        """Clear all pipeline state (for --force / fresh run)."""
        self.draft["_pipeline_state"] = {}

    def summary(self) -> str:
        """Human-readable status of all stages."""
        lines = []
        for stage in REFERENCE_PIPELINE_STAGES:
            entry = self.state.get(stage, {})
            status = entry.get("status", "pending")
            marker = {"done": "+", "failed": "!", "pending": " "}.get(status, "?")
            lines.append(f"  [{marker}] {stage}")
        return "\n".join(lines)

    def save(self, path: Any) -> None:
        """Write the draft (with embedded state) to disk."""
        target = str(path)
        os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
        tmp = target + ".part"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(self.draft, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, target)

    def reusable(self, stage: str, require: Optional[List[str]] = None) -> bool:
        """P7 enhancement: done is not enough, files must still be on disk and >= 64 bytes."""
        if not self._files_present(stage):
            return False
        for dep in require or []:
            if not self._files_present(dep):
                return False
        return True

    def _files_present(self, stage: str) -> bool:
        entry = self.state.get(stage) or {}
        if entry.get("status") != "done":
            return False
        files = entry.get("files") or []
        if not files:
            return True
        for path in files:
            if not path or not os.path.isfile(path) or os.path.getsize(path) < 64:
                return False
        return True
