# -*- coding: utf-8 -*-
"""
Deterministic Pipeline State Machine (Chapter 1 / Section 1.3 Master Plan).

Implements the 10-step sequential orchestration pipeline:
1. İstek Kabulü ve Doğrulama (STAGE_1_VALIDATION: 0% - 5%)
2. Kanca ve Anlatı Üretimi (STAGE_2_HOOK_NARRATIVE: 5% - 15%)
3. Senaryo Derleme (STAGE_3_DIRECTOR_PLAN: 15% - 25%)
4. Özgünlük Kontrolü (STAGE_4_ORIGINALITY_GATE: 25% - 30%)
5. Varlık Edinimi (STAGE_5_ASSET_INGESTION: 30% - 55%)
6. Seslendirme ve Zamanlama (STAGE_6_TTS_SYNC: 55% - 65%)
7. Akustik Tasarım ve Miksaj (STAGE_7_AUDIO_MASTERING: 65% - 75%)
8. Kinetik Altyazı Derleme (STAGE_8_SUBTITLE_COMPILE: 75% - 82%)
9. FFmpeg FilterComplex Render (STAGE_9_FFMPEG_RENDER: 82% - 95%)
10. Paketleme ve Dağıtım (STAGE_10_PACKAGING: 95% - 100%)
"""
from __future__ import annotations

import enum
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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


class PipelineStateMachine:
    """
    Orchestrates the 10-step video render lifecycle.
    Guarantees deterministic state transitions, telemetry metrics, and UI sync.
    """

    def __init__(self, job_id: str = "", keyword: str = "", niche_id: str = ""):
        self.job_id = job_id or f"job_{int(time.time())}"
        self.keyword = keyword
        self.niche_id = niche_id
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.current_stage: PipelineStage = PipelineStage.STAGE_1_VALIDATION
        self.current_pct: float = 0.0
        self.history: List[StageExecutionRecord] = []
        self._active_record: Optional[StageExecutionRecord] = None
        self._error: Optional[str] = None
        self._video_url: Optional[str] = None
        self.project_dir = ""
        self._resume_stages: Dict[str, Dict[str, Any]] = {}

        # Initialize first stage
        self.transition_to(
            PipelineStage.STAGE_1_VALIDATION,
            f"İşlem başlatılıyor: '{keyword}' (Niş: {niche_id})",
            pct=2.0,
        )

    def transition_to(
        self,
        stage: PipelineStage,
        message: str = "",
        pct: Optional[float] = None,
    ) -> float:
        """
        Transition to a new pipeline stage, closing the previous stage record.
        Emits progress and log telemetry.
        """
        now = time.time()
        spec = STAGE_SPECS.get(stage, STAGE_SPECS[PipelineStage.STAGE_1_VALIDATION])

        # Close active record if any
        if self._active_record and self._active_record.status == "running":
            self._active_record.ended_at = now
            self._active_record.duration_sec = round(now - self._active_record.started_at, 3)
            self._active_record.status = "done" if stage != PipelineStage.FAILED else "failed"
            self._active_record.end_pct = self.current_pct

        # Determine target percentage
        if pct is not None:
            clamped_pct = max(spec.min_pct, min(spec.max_pct, float(pct)))
        else:
            clamped_pct = spec.min_pct

        self.current_stage = stage
        self.current_pct = round(clamped_pct, 1)

        # Create new execution record
        new_record = StageExecutionRecord(
            stage=stage,
            order=spec.order,
            name_tr=spec.name_tr,
            started_at=now,
            start_pct=self.current_pct,
            message=message or spec.description,
            status="running" if stage not in (PipelineStage.COMPLETED, PipelineStage.FAILED) else ("completed" if stage == PipelineStage.COMPLETED else "failed"),
        )
        if stage in (PipelineStage.COMPLETED, PipelineStage.FAILED):
            new_record.ended_at = now
            new_record.end_pct = self.current_pct

        self._active_record = new_record
        self.history.append(new_record)

        # Broadcast state
        step_label = f"[{spec.order}/10] {spec.name_tr}" if spec.order <= 10 else spec.name_tr
        self._sync_global_state(self.current_pct, step_label, message)
        return self.current_pct

    def update_progress(self, pct: float, detail: str = "") -> float:
        """
        Update percentage within the currently active stage boundary.
        """
        spec = STAGE_SPECS.get(self.current_stage)
        if not spec:
            return self.current_pct

        clamped = max(spec.min_pct, min(spec.max_pct, float(pct)))
        self.current_pct = round(clamped, 1)

        step_label = f"[{spec.order}/10] {spec.name_tr}" if spec.order <= 10 else spec.name_tr
        self._sync_global_state(self.current_pct, step_label, detail)
        return self.current_pct

    def complete(self, video_url: str, message: str = "Tüm aşamalar tamamlandı."):
        """Mark pipeline as successfully completed."""
        self._video_url = video_url
        self.transition_to(PipelineStage.COMPLETED, message=message, pct=100.0)
        try:
            from server_core import state
            state.broadcast_event("complete", {"url": video_url, "message": message})
        except Exception:
            pass

    def fail(self, error_message: str):
        """Mark pipeline as failed."""
        self._error = error_message
        self.transition_to(PipelineStage.FAILED, message=f"HARD-FAIL: {error_message}", pct=self.current_pct)
        try:
            from server_core import state
            state.broadcast_event("error", error_message)
        except Exception:
            pass

    def export_telemetry(self) -> Dict[str, Any]:
        """Produce a complete execution report of all stages and timings."""
        records = []
        total_time = 0.0
        for r in self.history:
            dur = r.duration_sec
            if r.status == "running" and r.started_at:
                dur = round(time.time() - r.started_at, 3)
            records.append({
                "stage": r.stage.value,
                "order": r.order,
                "name": r.name_tr,
                "duration_sec": dur,
                "start_pct": r.start_pct,
                "end_pct": r.end_pct,
                "status": r.status,
                "message": r.message,
            })
            total_time += dur

        return {
            "job_id": self.job_id,
            "keyword": self.keyword,
            "niche_id": self.niche_id,
            "created_at": self.created_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "final_stage": self.current_stage.value,
            "final_pct": self.current_pct,
            "total_duration_sec": round(total_time, 2),
            "video_url": self._video_url,
            "error": self._error,
            "stages": records,
        }

    def save_telemetry(self, project_dir: str) -> Optional[str]:
        """Save telemetry JSON to project folder."""
        if not project_dir or not os.path.exists(project_dir):
            return None
        target_path = os.path.join(project_dir, "pipeline_execution_telemetry.json")
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(self.export_telemetry(), f, ensure_ascii=False, indent=2)
            return target_path
        except Exception as err:
            logger.warning(f"Failed to save pipeline telemetry: {err}")
            return None

    def bind_project(self, project_dir: str, resume: bool = False) -> None:
        """
        youtube-shorts-pipeline PipelineState.save writes the draft and
        is_done trusts the status flag alone. A deleted wav still counts
        as done. Here the checkpoint loads only when resume is true, and a
        stage is reusable only when every recorded file still exists.
        """
        self.project_dir = project_dir or ""
        self._resume_stages: Dict[str, Dict[str, Any]] = {}
        if not resume or not self.project_dir:
            return
        path = os.path.join(self.project_dir, "pipeline_state.json")
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            stages = payload.get("stages") if isinstance(payload, dict) else None
            if isinstance(stages, dict):
                self._resume_stages = stages
        except Exception as err:
            logger.warning(f"pipeline_state.json okunamadı: {err}")
            self._resume_stages = {}

    @staticmethod
    def _stage_key(stage: PipelineStage | str) -> str:
        if isinstance(stage, PipelineStage):
            return stage.value
        return str(stage)

    def is_done(self, stage: PipelineStage | str) -> bool:
        """Reference compatibility: check if stage completed successfully."""
        entry = self._resume_stages.get(self._stage_key(stage)) or {}
        return entry.get("status") == "done"

    def is_failed(self, stage: PipelineStage | str) -> bool:
        """Reference compatibility: check if stage status == 'failed'."""
        entry = self._resume_stages.get(self._stage_key(stage)) or {}
        return entry.get("status") == "failed"

    def stage_artifacts(self, stage: PipelineStage | str) -> Dict[str, Any]:
        entry = self._resume_stages.get(self._stage_key(stage)) or {}
        artifacts = entry.get("artifacts") or {}
        return artifacts if isinstance(artifacts, dict) else {}

    def get_artifact(self, stage: PipelineStage | str, key: str, default: Any = None) -> Any:
        """Reference compatibility: get artifact value from a completed stage."""
        artifacts = self.stage_artifacts(stage)
        return artifacts.get(key, default)

    def mark_done(
        self,
        stage: PipelineStage | str,
        artifacts: Optional[Dict[str, Any]] = None,
        files: Optional[List[str]] = None,
    ) -> None:
        self._resume_stages[self._stage_key(stage)] = {
            "status": "done",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "artifacts": artifacts or {},
            "files": [p for p in (files or []) if p],
        }
        self._write_checkpoint()

    def complete_stage(
        self,
        stage: PipelineStage | str,
        artifacts: Optional[Dict[str, Any]] = None,
        files: Optional[List[str]] = None,
    ) -> None:
        """Reference compatibility: alias for mark_done."""
        self.mark_done(stage, artifacts=artifacts, files=files)

    def fail_stage(self, stage: PipelineStage | str, error: str = "") -> None:
        """Reference compatibility: record failure for a specific stage."""
        self._resume_stages[self._stage_key(stage)] = {
            "status": "failed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error,
        }
        self._write_checkpoint()

    def invalidate_from(self, stage: PipelineStage | str) -> None:
        """A regenerated stage makes later checkpoints stale."""
        key = self._stage_key(stage)
        try:
            target_stage = PipelineStage(key)
            start = STAGE_SPECS[target_stage].order
        except (ValueError, KeyError):
            start = 0

        for name in list(self._resume_stages):
            try:
                later = PipelineStage(name)
            except ValueError:
                continue
            spec = STAGE_SPECS.get(later)
            if spec and spec.order >= start:
                self._resume_stages[name]["status"] = "stale"
        self._write_checkpoint()

    def reset(self) -> None:
        """Reference compatibility: reset all checkpoint stages."""
        self._resume_stages = {}
        self._write_checkpoint()

    def summary(self) -> str:
        """Reference compatibility: human-readable status overview of all pipeline stages."""
        lines = []
        for st in PipelineStage:
            if st in (PipelineStage.COMPLETED, PipelineStage.FAILED):
                continue
            entry = self._resume_stages.get(st.value, {})
            status = entry.get("status", "pending")
            marker = {"done": "+", "failed": "!", "stale": "~", "pending": " "}.get(status, "?")
            spec = STAGE_SPECS.get(st)
            name = spec.name_tr if spec else st.value
            lines.append(f"  [{marker}] {st.value} ({name})")
        return "\n".join(lines)

    def save(self, path: Optional[str] = None) -> None:
        """Reference compatibility: save draft/checkpoint to disk."""
        if path:
            target = str(path)
            os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
            payload = {
                "job_id": self.job_id,
                "keyword": self.keyword,
                "niche_id": self.niche_id,
                "stages": self._resume_stages,
            }
            tmp = target + ".part"
            with open(tmp, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(tmp, target)
        else:
            self._write_checkpoint()

    def reusable(self, stage: PipelineStage | str, require: Optional[List[PipelineStage | str]] = None) -> bool:
        """Done is not enough. Every recorded file must still be on disk."""
        if not self._files_present(stage):
            return False
        for dep in require or []:
            if not self._files_present(dep):
                return False
        return True

    def _files_present(self, stage: PipelineStage | str) -> bool:
        entry = self._resume_stages.get(self._stage_key(stage)) or {}
        if entry.get("status") != "done":
            return False
        files = entry.get("files") or []
        if not files:
            return False
        for path in files:
            if not path or not os.path.isfile(path) or os.path.getsize(path) < 64:
                return False
        return True

    def _write_checkpoint(self) -> None:
        if not getattr(self, "project_dir", ""):
            return
        os.makedirs(self.project_dir, exist_ok=True)
        target = os.path.join(self.project_dir, "pipeline_state.json")
        payload = {
            "job_id": self.job_id,
            "keyword": self.keyword,
            "niche_id": self.niche_id,
            "stages": self._resume_stages,
        }
        tmp = target + ".part"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, target)

    def _sync_global_state(self, pct: float, step: str, msg: str = ""):
        try:
            from server_core import state
            state.current_render_state["percent"] = pct
            state.current_render_state["step"] = step
            state.current_render_state["stage"] = self.current_stage.value
            state.broadcast_event("progress", {"percent": pct, "step": step, "stage": self.current_stage.value})
            if msg:
                state.broadcast_event("log", msg)
        except Exception:
            pass


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
