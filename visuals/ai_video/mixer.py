"""Per-scene visual source mixer: AI + stock + procedural as equal peers."""
from __future__ import annotations

import hashlib
import os
import random
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple


class VisualSource(str, Enum):
    AI = "ai"
    STOCK = "stock"
    PROCEDURAL = "procedural"


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except (TypeError, ValueError):
        return default


def niche_bias(niche_id: str = "") -> Dict[VisualSource, float]:
    """Multipliers on mix weights (not absolute)."""
    n = (niche_id or "").lower()
    # defaults
    m = {VisualSource.AI: 1.0, VisualSource.STOCK: 1.0, VisualSource.PROCEDURAL: 1.0}
    if any(k in n for k in ("relig", "islam", "din", "spiritual", "motivation_faith")):
        m[VisualSource.AI] = 0.45          # fewer AI faces / sacred risk
        m[VisualSource.STOCK] = 1.15
        m[VisualSource.PROCEDURAL] = 1.55  # calligraphy / kinetic
    elif any(k in n for k in ("crypto", "finans", "finance", "trading", "bitcoin")):
        m[VisualSource.AI] = 1.45
        m[VisualSource.STOCK] = 1.1
        m[VisualSource.PROCEDURAL] = 0.7
    elif any(k in n for k in ("tech", "ai_", "science", "uzay", "space")):
        m[VisualSource.AI] = 1.25
        m[VisualSource.STOCK] = 0.9
        m[VisualSource.PROCEDURAL] = 1.0
    elif any(k in n for k in ("story", "hikaye", "reddit", "horror")):
        m[VisualSource.AI] = 1.1
        m[VisualSource.STOCK] = 1.0
        m[VisualSource.PROCEDURAL] = 1.15
    elif any(k in n for k in ("kids", "cocuk", "çocuk", "kids_animation", "36_kids")):
        # Kids Shorts: AI cartoon high; stock only soft nature/animals; procedural pastels
        m[VisualSource.AI] = 1.7
        m[VisualSource.STOCK] = 0.55
        m[VisualSource.PROCEDURAL] = 1.25
    return m


def mix_weights(
    niche_id: str = "",
    *,
    ai: Optional[float] = None,
    stock: Optional[float] = None,
    procedural: Optional[float] = None,
    ai_available: bool = True,
) -> Dict[VisualSource, float]:
    w = {
        VisualSource.AI: ai if ai is not None else _env_float("VISUAL_MIX_AI", 0.4),
        VisualSource.STOCK: stock if stock is not None else _env_float("VISUAL_MIX_STOCK", 0.4),
        VisualSource.PROCEDURAL: procedural if procedural is not None else _env_float("VISUAL_MIX_PROCEDURAL", 0.2),
    }
    bias = niche_bias(niche_id)
    for k in w:
        w[k] = max(0.0, float(w[k]) * bias[k])
    if not ai_available:
        w[VisualSource.AI] = 0.0
    total = sum(w.values())
    if total <= 0:
        return {VisualSource.STOCK: 0.5, VisualSource.PROCEDURAL: 0.5, VisualSource.AI: 0.0}
    return {k: v / total for k, v in w.items()}


def _rng(seed: Optional[str], scene_index: int) -> random.Random:
    env_seed = (os.getenv("VISUAL_MIX_SEED") or "").strip()
    base = seed or env_seed or "youtubeoto"
    h = hashlib.md5(f"{base}:{scene_index}".encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def assign_visual_source(
    scene_index: int = 0,
    *,
    niche_id: str = "",
    seed: Optional[str] = None,
    ai_available: bool = True,
    weights: Optional[Dict[VisualSource, float]] = None,
) -> VisualSource:
    """
    Weighted pick with light beat patterning: even scenes lean stock/AI,
    odd lean procedural slightly — then RNG on remaining mass.
    """
    w = dict(weights or mix_weights(niche_id, ai_available=ai_available))
    # Beat nudge: distribute variety across consecutive scenes
    if scene_index % 3 == 2 and w.get(VisualSource.PROCEDURAL, 0) > 0:
        w[VisualSource.PROCEDURAL] = w.get(VisualSource.PROCEDURAL, 0) + 0.08
    elif scene_index % 3 == 0 and w.get(VisualSource.AI, 0) > 0:
        w[VisualSource.AI] = w.get(VisualSource.AI, 0) + 0.06
    elif w.get(VisualSource.STOCK, 0) > 0:
        w[VisualSource.STOCK] = w.get(VisualSource.STOCK, 0) + 0.05
    total = sum(w.values()) or 1.0
    items: List[Tuple[VisualSource, float]] = [(k, v / total) for k, v in w.items() if v > 0]
    if not items:
        return VisualSource.PROCEDURAL
    r = _rng(seed, scene_index).random()
    acc = 0.0
    for src, p in items:
        acc += p
        if r <= acc:
            return src
    return items[-1][0]


def peer_failover_order(
    primary: VisualSource,
    *,
    niche_id: str = "",
    ai_available: bool = True,
) -> List[VisualSource]:
    """Primary first, then remaining peers sorted by mix weight (never blank)."""
    w = mix_weights(niche_id, ai_available=ai_available)
    others = sorted(
        (s for s in VisualSource if s != primary and w.get(s, 0) >= 0),
        key=lambda s: w.get(s, 0),
        reverse=True,
    )
    # Always keep procedural as final safety even if weight 0
    order = [primary] + [s for s in others if s != VisualSource.PROCEDURAL]
    if VisualSource.PROCEDURAL not in order:
        order.append(VisualSource.PROCEDURAL)
    elif order[-1] != VisualSource.PROCEDURAL:
        order = [s for s in order if s != VisualSource.PROCEDURAL] + [VisualSource.PROCEDURAL]
    # Drop AI if unavailable
    if not ai_available:
        order = [s for s in order if s != VisualSource.AI]
    return order
