"""
Active Speaker & Multi-Face Layout Service.
Adapted from mutonby/openshorts (active_speaker.py & layout_picker.py).

Analyzes speech activity and multi-speaker dialogues to route video layout:
  - Single speaker -> Centered 9:16 portrait crop
  - Two active conversationalists -> Dynamic split-screen stack (Top/Bottom) or turn-based camera cut
  - Silent listener -> Focuses solely on whoever is holding the floor instead of wasting half the frame
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class LayoutDecision(str, Enum):
    SINGLE_PORTRAIT = "single_portrait"
    SPLIT_STACK = "split_stack"
    DYNAMIC_SWITCHING = "dynamic_switching"
    SCREENCAST_INSET = "screencast_inset"


@dataclass
class SpeakerTurn:
    speaker_id: str
    start_sec: float
    end_sec: float

    @property
    def duration_sec(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)


@dataclass
class SpeakerAuditResult:
    layout_decision: LayoutDecision
    speaker_turns: List[SpeakerTurn]
    speaker_distribution: Dict[str, float]  # speaker_id -> share (0.0 to 1.0)
    is_multispeaker: bool
    explanation: str


class ActiveSpeakerDetector:
    """Routes conversational layouts based on dialogue turn-taking and speech activity."""

    MIN_CONVERSATION_SHARE: float = 0.20  # Speaker needs >=20% share to justify split stack

    @classmethod
    def evaluate_turns(
        cls,
        turns: List[Dict[str, Any]],
        total_duration_sec: float,
    ) -> SpeakerAuditResult:
        """
        Evaluates a list of speaker turns.
        turns schema: [{"speaker": "A", "start": 0.0, "end": 4.5}, {"speaker": "B", "start": 4.6, "end": 8.2}]
        """
        if not turns or total_duration_sec <= 0:
            return SpeakerAuditResult(
                layout_decision=LayoutDecision.SINGLE_PORTRAIT,
                speaker_turns=[],
                speaker_distribution={"speaker_0": 1.0},
                is_multispeaker=False,
                explanation="No multi-speaker turns detected. Defaulting to single portrait crop.",
            )

        speaker_durations: Dict[str, float] = {}
        parsed_turns: List[SpeakerTurn] = []

        for t in turns:
            spk = str(t.get("speaker") or t.get("speaker_id") or "speaker_A")
            s = float(t.get("start") or 0.0)
            e = float(t.get("end") or s + 1.0)
            dur = max(0.1, e - s)
            speaker_durations[spk] = speaker_durations.get(spk, 0.0) + dur
            parsed_turns.append(SpeakerTurn(speaker_id=spk, start_sec=s, end_sec=e))

        sum_dur = sum(speaker_durations.values()) or total_duration_sec
        distribution = {spk: round(d / sum_dur, 3) for spk, d in speaker_durations.items()}

        active_speakers = [spk for spk, share in distribution.items() if share >= cls.MIN_CONVERSATION_SHARE]

        if len(active_speakers) >= 2:
            # Active dialogue! Decide between Split Stack or Dynamic Switching
            # If turns are rapid (<3s per turn) -> Split Stack is best to avoid jump-cut nausea
            avg_turn_dur = sum_dur / max(len(parsed_turns), 1)
            if avg_turn_dur < 3.5:
                decision = LayoutDecision.SPLIT_STACK
                expl = (
                    f"Two active speakers ({distribution}) with rapid turn-taking ({avg_turn_dur:.1f}s avg). "
                    f"Routing to vertical split-screen stack."
                )
            else:
                decision = LayoutDecision.DYNAMIC_SWITCHING
                expl = (
                    f"Two active speakers ({distribution}) with distinct monologue segments ({avg_turn_dur:.1f}s avg). "
                    f"Routing to dynamic camera switching."
                )
            is_multi = True
        else:
            decision = LayoutDecision.SINGLE_PORTRAIT
            primary_spk = max(distribution.items(), key=lambda x: x[1])[0]
            expl = (
                f"Single dominant speaker detected ({primary_spk} has {distribution[primary_spk]*100:.0f}% share). "
                f"Suppressing split layout to prevent empty/silent half-screen."
            )
            is_multi = False

        return SpeakerAuditResult(
            layout_decision=decision,
            speaker_turns=parsed_turns,
            speaker_distribution=distribution,
            is_multispeaker=is_multi,
            explanation=expl,
        )


active_speaker_detector = ActiveSpeakerDetector()
