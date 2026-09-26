"""Helios (PKU-YuanGroup) 14B Real-Time Long Video Generation Provider."""
from __future__ import annotations

import os
import shutil
from typing import Optional

import requests

from ..base import AIVideoProvider, AIVideoResult
from ..helios_prompt_builder import HeliosPromptBuilder, HELIOS_NEGATIVE_PROMPT
from ..http_util import ai_generated_license, download_url, env_key, log_skip_once, write_bytes


class HeliosVideoProvider(AIVideoProvider):
    name = "helios"
    # Priority 8: high priority (right behind truly local comfy/wan, ahead of paid clouds)
    priority = 8

    def is_available(self) -> bool:
        return bool(env_key("HELIOS_API_URL", "HELIOS_ENDPOINT", "HELIOS_URL"))

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 4.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        base = env_key("HELIOS_API_URL", "HELIOS_ENDPOINT", "HELIOS_URL").rstrip("/")
        if not base:
            log_skip_once(self.name, "HELIOS_API_URL missing")
            return None

        # Build parameters tuned to Helios model architecture
        params = HeliosPromptBuilder.create_helios_params(
            narration=prompt,
            scene_description=prompt,
            duration=duration,
            aspect=aspect,
            distilled=True,
        )

        payload = {
            "prompt": params.prompt,
            "negative_prompt": params.negative_prompt,
            "height": params.height,
            "width": params.width,
            "num_frames": params.num_frames,
            "fps": params.fps,
            "guidance_scale": params.guidance_scale,
            "pyramid_num_inference_steps_list": params.pyramid_steps,
            "is_amplify_first_chunk": params.is_amplify_first_chunk,
            "seed": seed if seed is not None else 42,
        }

        token = env_key("HELIOS_API_KEY", "HELIOS_TOKEN")
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            # 1. Post to Helios inference endpoint
            endpoint_url = f"{base}/generate" if not base.endswith("/generate") else base
            r = requests.post(endpoint_url, json=payload, headers=headers, timeout=360)
            if r.status_code != 200:
                print(f"    [AI-VIDEO:helios] HTTP {r.status_code}: {r.text[:200]}")
                return None

            path: Optional[str] = None
            if "application/json" in (r.headers.get("content-type") or ""):
                data = r.json()
                video_url = data.get("url") or data.get("video_url") or data.get("output")
                local_file = data.get("path") or data.get("file_path")
                if local_file and os.path.isfile(local_file):
                    shutil.copy2(local_file, output_path)
                    path = output_path
                elif video_url:
                    if download_url(video_url, output_path):
                        path = output_path
            else:
                # Raw MP4 stream
                if r.content[:4] in (b"\x00\x00\x00\x18", b"\x00\x00\x00\x1c", b"ftyp") or len(r.content) > 10_000:
                    if write_bytes(r.content, output_path):
                        path = output_path

            if not path or not os.path.isfile(path):
                return None

            return AIVideoResult(
                path=path,
                provider=self.name,
                model="helios-14b-distilled",
                prompt=params.prompt,
                seed=seed,
                duration=duration,
                aspect=aspect,
                license=ai_generated_license(self.name, "helios-14b-distilled"),
                raw={"frames": params.num_frames, "fps": params.fps},
            )
        except Exception as exc:
            print(f"    [AI-VIDEO:helios] error: {exc}")
            return None
