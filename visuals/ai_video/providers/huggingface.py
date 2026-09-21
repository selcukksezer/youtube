"""Hugging Face Inference Providers text-to-video adapter."""
from __future__ import annotations

from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, env_key, log_skip_once, write_bytes

_DEFAULT_MODEL = "Wan-AI/Wan2.1-T2V-1.3B"


class HuggingFaceVideoProvider(AIVideoProvider):
    name = "huggingface"
    priority = 15

    def is_available(self) -> bool:
        return bool(env_key("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGINGFACEHUB_API_TOKEN"))

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        token = env_key("HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGINGFACEHUB_API_TOKEN")
        if not token:
            log_skip_once(self.name, "HF_TOKEN missing")
            return None
        model = env_key("HF_VIDEO_MODEL") or _DEFAULT_MODEL
        # Prefer InferenceClient when installed
        try:
            from huggingface_hub import InferenceClient
            client = InferenceClient(provider="fal-ai", api_key=token)
            video = client.text_to_video(prompt, model=model)
            data = video if isinstance(video, (bytes, bytearray)) else getattr(video, "data", None) or bytes(video)
            if data and write_bytes(bytes(data), output_path):
                return AIVideoResult(
                    path=output_path,
                    provider=self.name,
                    model=model,
                    prompt=prompt,
                    seed=seed,
                    duration=duration,
                    aspect=aspect,
                    license=ai_generated_license(self.name, model),
                )
        except ImportError:
            pass
        except Exception as exc:
            print(f"    [AI-VIDEO:huggingface] client: {exc}")

        # Raw router fallback
        url = f"https://router.huggingface.co/hf-inference/models/{model}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body = {"inputs": prompt, "parameters": {}}
        if seed is not None:
            body["parameters"]["seed"] = int(seed)
        try:
            r = requests.post(url, headers=headers, json=body, timeout=180)
            if r.status_code in (401, 403):
                log_skip_once(self.name, f"auth HTTP {r.status_code}")
                return None
            if r.status_code == 402:
                log_skip_once(self.name, "monthly credits exhausted")
                return None
            ctype = (r.headers.get("content-type") or "").lower()
            if r.status_code == 200 and ("video" in ctype or "octet" in ctype or r.content[:4] == b"\x00\x00\x00"):
                if write_bytes(r.content, output_path):
                    return AIVideoResult(
                        path=output_path,
                        provider=self.name,
                        model=model,
                        prompt=prompt,
                        seed=seed,
                        duration=duration,
                        aspect=aspect,
                        license=ai_generated_license(self.name, model),
                    )
            print(f"    [AI-VIDEO:huggingface] HTTP {r.status_code}: {r.text[:180]}")
        except Exception as exc:
            print(f"    [AI-VIDEO:huggingface] {exc}")
        return None
