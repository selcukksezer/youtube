"""Create a visual-evidence-grounded narration draft from sampled video frames."""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import requests

import config
from services.video_title_ideas import _request_gemini_json, _sample_frames


class DocumentaryNarrationError(RuntimeError):
    """Raised when frame analysis or narration generation returns invalid data."""


class DocumentaryNarrationUnavailable(DocumentaryNarrationError):
    """Raised when Gemini is not configured for visual narration generation."""


def generate_documentary_narration(
    video_path: str,
    *,
    theme: str = "",
) -> Dict[str, Any]:
    """Analyze up to eight sampled frames and write a short Turkish narration."""
    if not isinstance(theme, str):
        raise ValueError("theme must be text.")
    theme = theme.strip()
    if len(theme) > 240:
        raise ValueError("theme must be at most 240 characters.")
    if not video_path or not os.path.isfile(video_path):
        raise FileNotFoundError("Video dosyası bulunamadı.")

    api_key = str(getattr(config, "GEMINI_API_KEY", "") or "").strip()
    if not api_key:
        raise DocumentaryNarrationUnavailable(
            "Görsel anlatım için GEMINI_API_KEY yapılandırılmamış."
        )

    frames = _sample_frames(video_path)
    if not frames:
        raise DocumentaryNarrationError(
            "Videodan analiz edilebilir örnek kare çıkarılamadı."
        )

    theme_text = theme or "videodaki ana olay akışı"
    prompt = f"""Sen, YouTube Shorts için görsel kanıta bağlı Türkçe anlatım yazarı.
Ekli {len(frames)} kare kaynak videodan zaman sırasıyla ve eşit aralıklarla örneklenmiştir.
Kareler arasındaki görünmeyen olayları, konuşmaları, kişi kimliklerini veya nedenleri uydurma.
Kullanıcının odak isteği: {theme_text}

Yaklaşık 30 saniyelik, 60-85 kelimelik, doğal okunabilir bir Türkçe seslendirme taslağı yaz.
İlk cümlede somut bir görsel kanca kur; devamında yalnızca karelerin desteklediği olay akışını anlat.
Bir cümlelik tarafsız özet ve her kare için tek kısa gözlem de üret.
frame_observations dizisi tam olarak {len(frames)} öğe içermeli ve kare sırasını korumalı.
Çıktı şeması:
{{"summary":"...","narration":"...","frame_observations":["..."]}}
Yalnızca geçerli JSON döndür."""

    model = str(
        getattr(config, "GEMINI_MODEL", "") or "gemini-flash-lite-latest"
    ).strip()
    try:
        result = _request_gemini_json(
            api_key=api_key,
            model=model,
            prompt=prompt,
            frames=frames,
        )
    except requests.RequestException as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        detail = f"HTTP {status}" if status is not None else type(exc).__name__
        raise DocumentaryNarrationError(
            f"Gemini kare analizi isteği başarısız oldu ({detail})."
        ) from exc
    except (ValueError, TypeError, AttributeError) as exc:
        raise DocumentaryNarrationError(
            f"Gemini kare analizi yanıtı okunamadı ({type(exc).__name__})."
        ) from exc

    summary = result.get("summary")
    narration = result.get("narration")
    raw_observations = result.get("frame_observations")
    if not isinstance(summary, str) or not summary.strip():
        raise DocumentaryNarrationError("Gemini yanıtında geçerli bir özet yok.")
    if not isinstance(narration, str) or not narration.strip():
        raise DocumentaryNarrationError("Gemini yanıtında geçerli bir anlatım taslağı yok.")
    if not isinstance(raw_observations, list) or len(raw_observations) != len(frames):
        raise DocumentaryNarrationError(
            "Gemini yanıtındaki kare gözlemleri örnek kare sayısıyla eşleşmiyor."
        )

    observations: List[str] = []
    for observation in raw_observations:
        if not isinstance(observation, str) or not observation.strip():
            raise DocumentaryNarrationError(
                "Gemini yanıtında boş veya geçersiz kare gözlemi var."
            )
        observations.append(" ".join(observation.split())[:240])

    clean_narration = re.sub(r"[ \t]+", " ", narration).strip()
    if len(clean_narration) > 2500:
        raise DocumentaryNarrationError(
            "Gemini anlatım taslağı beklenen uzunluğu aşıyor."
        )
    return {
        "summary": " ".join(summary.split())[:600],
        "narration": clean_narration,
        "frame_observations": observations,
        "frames_analyzed": len(frames),
        "language": "tr",
    }
