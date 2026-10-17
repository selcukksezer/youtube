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

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .pipeline_state_helpers import (
    REFERENCE_PIPELINE_STAGES,
    STAGE_SPECS,
    PipelineStage,
    PipelineState,
    StageExecutionRecord,
    StageMetadata,
)

logger = logging.getLogger(__name__)


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

        if self._active_record and self._active_record.status == "running":
            self._active_record.ended_at = now
            self._active_record.duration_sec = round(now - self._active_record.started_at, 3)
            self._active_record.status = "done" if stage != PipelineStage.FAILED else "failed"
            self._active_record.end_pct = self.current_pct

        if pct is not None:
            clamped_pct = max(spec.min_pct, min(spec.max_pct, float(pct)))
        else:
            clamped_pct = spec.min_pct

        self.current_stage = stage
        self.current_pct = round(clamped_pct, 1)

        new_record = StageExecutionRecord(
            stage=stage,
            order=spec.order,
            name_tr=spec.name_tr,
            started_at=now,
            start_pct=self.current_pct,
            message=message or spec.description,
            status=(
                "running"
                if stage not in (PipelineStage.COMPLETED, PipelineStage.FAILED)
                else ("completed" if stage == PipelineStage.COMPLETED else "failed")
            ),
        )
        if stage in (PipelineStage.COMPLETED, PipelineStage.FAILED):
            new_record.ended_at = now
            new_record.end_pct = self.current_pct

        self._active_record = new_record
        self.history.append(new_record)

        step_label = f"[{spec.order}/10] {spec.name_tr}" if spec.order <= 10 else spec.name_tr
        self._sync_global_state(self.current_pct, step_label, message)
        return self.current_pct

    def update_progress(self, pct: float, detail: str = "") -> float:
        """Update percentage within the currently active stage boundary."""
        spec = STAGE_SPECS.get(self.current_stage)
        if not spec:
            return self.current_pct

        clamped = max(spec.min_pct, min(spec.max_pct, float(pct)))
        self.current_pct = round(clamped, 1)

        step_label = f"[{spec.order}/10] {spec.name_tr}" if spec.order <= 10 else spec.name_tr
        self._sync_global_state(self.current_pct, step_label, detail)
        return self.current_pct

    def complete(self, video_url: str, message: str = "Tüm aşamalar tamamlandı.", *, broadcast: bool = True):
        """Mark pipeline as successfully completed."""
        self._video_url = video_url
        self.transition_to(PipelineStage.COMPLETED, message=message, pct=100.0)
        if broadcast:
            try:
                from server_core import state
                state.broadcast_event("complete", {"url": video_url, "message": message})
            except Exception:
                logger.warning(
                    "Failed to broadcast render completion for job %s",
                    self.job_id,
                    exc_info=True,
                )

    def fail(self, error_message: str, *, broadcast: bool = True):
        """Mark pipeline as failed."""
        self._error = error_message
        self.transition_to(PipelineStage.FAILED, message=f"HARD-FAIL: {error_message}", pct=self.current_pct)
        if broadcast:
            try:
                from server_core import state
                state.broadcast_event("error", error_message)
            except Exception:
                logger.warning(
                    "Failed to broadcast render failure for job %s",
                    self.job_id,
                    exc_info=True,
                )

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
            logger.warning(
                "Failed to sync render progress for job %s",
                self.job_id,
                exc_info=True,
            )


__all__ = [
    "PipelineStage",
    "PipelineState",
    "PipelineStateMachine",
    "REFERENCE_PIPELINE_STAGES",
    "STAGE_SPECS",
    "StageExecutionRecord",
    "StageMetadata",
]
