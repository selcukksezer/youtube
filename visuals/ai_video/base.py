"""Abstract AI video provider contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class AIVideoResult:
    path: str
    provider: str
    model: str = ""
    prompt: str = ""
    seed: Optional[int] = None
    duration: float = 0.0
    aspect: str = "9:16"
    license: Dict[str, Any] = field(default_factory=dict)
    cached: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_manifest(self, scene_index: int = 0) -> Dict[str, Any]:
        return {
            "scene_index": scene_index,
            "path": self.path,
            "uid": f"ai:{self.provider}:{self.model}:{scene_index}",
            "source": f"ai_{self.provider}",
            "id": self.model or self.provider,
            "title": f"AI video ({self.provider})",
            "kind": "ai_video",
            "prompt": self.prompt,
            "seed": self.seed,
            "cached": self.cached,
            "license": self.license or {
                "license": "ai_generated",
                "source": self.provider,
                "safe": True,
                "needs_attribution": True,
                "raw": f"Generated via {self.provider} {self.model}".strip(),
                "author": self.provider,
                "title": f"AI clip ({self.provider})",
            },
        }


class AIVideoProvider(ABC):
    name: str = "base"
    # Prefer lower = tried earlier within AI chain
    priority: int = 100

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        ...
