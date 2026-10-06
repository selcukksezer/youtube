"""
Bölüm 8.2: YouTube Tekrarlayan ve Otomatik İçerik Koruma Kalkanı
(YouTube Repetitive & Reused Content Defense Shield)

YouTube algoritmasının videoyu "tekrarlayan içerik" (reused/repetitive content) olarak
işaretlememesi için 3 katmanlı dijital parmak izi koruması:
1. Renk jiteri: RGB kanalları için bağımsız gamma ve kontrast mikro-varyasyonu (±%1.5)
2. Dinamik kare hızı çeşitlendirmesi: [29.97, 30.00, 30.02 fps]
3. Görünmez zamansal gürültü katmanı: noise=alls=3:allf=t
"""
from __future__ import annotations

import random
import re
from typing import Dict, Any, List, Optional, Tuple, Sequence, Union

# Kanonik kare hızı çeşitlendirme havuzu (Bölüm 8.2)
DIVERSIFIED_FPS_OPTIONS: Tuple[float, ...] = (29.97, 30.00, 30.02)
ALLOWED_DIVERSIFIED_FPS = DIVERSIFIED_FPS_OPTIONS

# Standart varyasyon aralığı (±%1.5)
DEFAULT_JITTER_RANGE: float = 0.015


def get_diversified_fps(
    options: Sequence[float] = DIVERSIFIED_FPS_OPTIONS,
    seed: Optional[Any] = None,
) -> float:
    """
    Bölüm 8.2: YouTube algoritmasının sabit kare hızına dayalı şablon eşlemesini
    kırmak için dinamik kare hızı çeşitlendirmesi (29.97, 30.00, 30.02 fps) seçer.
    """
    rng = random.Random(seed) if seed is not None else random
    return float(rng.choice(list(options)))


def get_rgb_color_jitter_filter(
    jitter_range: float = DEFAULT_JITTER_RANGE,
    seed: Optional[Any] = None,
    as_tuple: bool = False,
) -> Union[str, Tuple[str, Dict[str, float]]]:
    """
    Bölüm 8.2: RGB kanalları için bağımsız gamma ve kontrast mikro-varyasyonu (±%1.5).
    Her renderda farklı RGB ton dağılımı üreterek pHash benzerliğini bozar, insan gözü fark edemez.

    Returns:
        filter_str (str) if as_tuple=False else (filter_str, params)
    """
    rng = random.Random(seed) if seed is not None else random
    contrast = 1.0 + rng.uniform(-jitter_range, jitter_range)
    gamma_r = 1.0 + rng.uniform(-jitter_range, jitter_range)
    gamma_g = 1.0 + rng.uniform(-jitter_range, jitter_range)
    gamma_b = 1.0 + rng.uniform(-jitter_range, jitter_range)
    saturation = 1.0 + rng.uniform(-jitter_range, jitter_range)

    filter_str = (
        f"eq=contrast={contrast:.4f}:gamma_r={gamma_r:.4f}:"
        f"gamma_g={gamma_g:.4f}:gamma_b={gamma_b:.4f}:"
        f"saturation={saturation:.4f}"
    )
    if not as_tuple:
        return filter_str

    params = {
        "contrast": round(contrast, 4),
        "gamma_r": round(gamma_r, 4),
        "gamma_g": round(gamma_g, 4),
        "gamma_b": round(gamma_b, 4),
        "saturation": round(saturation, 4),
    }
    return filter_str, params


def get_temporal_noise_filter(strength: int = 3, flag: str = "t") -> str:
    """
    Bölüm 8.2: Görünmez zamansal gürültü katmanı.
    noise=alls=3:allf=t ile her karede zamansal olarak değişen mikro gürültü eklenir.
    Piksel hash'lerini ve video imzasını benzersiz kılar.
    """
    s = max(1, min(10, int(strength)))
    return f"noise=alls={s}:allf={flag}"


def build_anti_repetition_filter_chain(
    anti_duplicate: bool = True,
    jitter_range: float = DEFAULT_JITTER_RANGE,
    noise_strength: int = 3,
    soft_vignette: bool = True,
    include_vignette: Optional[bool] = None,
    seed: Optional[Any] = None,
) -> str:
    """
    Bölüm 8.2 koruma kalkanını tek bir FFmpeg filtre zincirinde birleştirir:
    RGB jiter + unsharp + temporal noise + vignette.
    """
    vignette_flag = include_vignette if include_vignette is not None else soft_vignette
    parts: List[str] = []

    # 1. RGB renk jiteri
    jitter_res = get_rgb_color_jitter_filter(jitter_range=jitter_range, seed=seed)
    jitter_str = jitter_res[0] if isinstance(jitter_res, tuple) else jitter_res
    parts.append(jitter_str)

    # 2. Unsharp maskesi (kenar imzası yenileme)
    parts.append("unsharp=5:5:0.8:5:5:0.0")

    # 3. Görünmez zamansal gürültü
    if anti_duplicate:
        parts.append(get_temporal_noise_filter(strength=noise_strength, flag="t"))

    # 4. Yumuşak köşe karartması (vignette)
    if vignette_flag:
        parts.append("vignette=PI/5")

    return ",".join(parts)


def audit_anti_repetition_shield(
    filter_chain: str = "",
    fps: float = 0.0,
    allowed_fps: Sequence[float] = DIVERSIFIED_FPS_OPTIONS,
    *,
    filter_complex_str: Optional[str] = None,
    rendered_fps: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Render edilen filtre zincirini ve kare hızını Bölüm 8.2 standartlarına göre denetler.
    """
    fc = str(filter_complex_str if filter_complex_str is not None else filter_chain or "")
    active_fps = rendered_fps if rendered_fps is not None else fps

    # 1. RGB Jitter kontrolü (Bağımsız gamma_r, gamma_g, gamma_b ve kontrast)
    has_rgb_gamma = bool("gamma_r=" in fc and "gamma_g=" in fc and "gamma_b=" in fc)
    has_contrast = "contrast=" in fc

    # 2. Zamansal gürültü kontrolü (noise=alls=...:allf=t)
    has_temporal_noise = bool(re.search(r"noise=alls=\d+:allf=t", fc))

    # 3. Kare hızı kontrolü
    fps_val = round(float(active_fps), 2)
    valid_fps = any(abs(fps_val - round(f, 2)) < 0.05 for f in allowed_fps)

    compliant = bool(has_rgb_gamma and has_contrast and has_temporal_noise and valid_fps)

    return {
        "compliant": compliant,
        "rgb_jitter": has_rgb_gamma and has_contrast,
        "has_rgb_jitter": has_rgb_gamma and has_contrast,
        "temporal_noise": has_temporal_noise,
        "has_temporal_noise": has_temporal_noise,
        "fps_diversified": valid_fps,
        "is_fps_diversified": valid_fps,
        "detected_fps": fps_val,
        "filter_chain": fc,
    }
