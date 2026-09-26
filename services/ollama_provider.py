"""
Ollama Local LLM Provider (Offline 0 TL AI Engine).
Adapted & enhanced from MoneyPrinterV2's local LLM architecture.

Provides:
- Auto-discovery of local Ollama server (http://localhost:11434).
- Model listing (llama3, mistral, qwen, gemma, phi3, etc.).
- OpenAI-compatible client wrapper for direct integration into scenes/generator.py.
- CircuitBreaker fallback integration when Gemini/OpenAI cloud quotas fail (429 / offline).
"""

from __future__ import annotations
import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional
from openai import OpenAI

logger = logging.getLogger("OllamaProvider")

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3:latest"


def is_ollama_available(base_url: str = DEFAULT_OLLAMA_BASE_URL, timeout: float = 2.0) -> bool:
    """Check if local Ollama daemon is active and responding."""
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, headers={"User-Agent": "ShortsVideoCreators"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status == 200
    except Exception:
        return False


def list_ollama_models(base_url: str = DEFAULT_OLLAMA_BASE_URL, timeout: float = 3.0) -> List[str]:
    """List all models installed in local Ollama daemon."""
    try:
        url = f"{base_url.rstrip('/')}/api/tags"
        req = urllib.request.Request(url, headers={"User-Agent": "ShortsVideoCreators"})
        with urllib.request.urlopen(req, timeout=timeout) as res:
            if res.status == 200:
                data = json.loads(res.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
                return sorted(models)
    except Exception as e:
        logger.debug(f"Failed to fetch Ollama models: {e}")
    return []


def get_preferred_ollama_model(base_url: str = DEFAULT_OLLAMA_BASE_URL) -> Optional[str]:
    """Pick best available local model for scriptwriting."""
    models = list_ollama_models(base_url)
    if not models:
        return None
    
    # Priority order for high-quality instruction & storytelling
    preferred_order = [
        "qwen2.5:latest", "qwen2.5:7b", "qwen:latest",
        "llama3.3:latest", "llama3.2:latest", "llama3.1:latest", "llama3:latest",
        "mistral:latest", "gemma2:latest", "phi3:latest", "deepseek-r1:latest"
    ]
    for pref in preferred_order:
        for m in models:
            if pref.split(":")[0] in m.lower():
                return m
    return models[0]


def generate_text_ollama(
    prompt: str,
    system_prompt: str = "You are a professional viral YouTube Shorts creator and scriptwriter.",
    model: Optional[str] = None,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
    temperature: float = 0.7,
    timeout: float = 60.0
) -> str:
    """Directly query Ollama API without external heavy libraries."""
    chosen_model = model or get_preferred_ollama_model(base_url) or DEFAULT_OLLAMA_MODEL
    url = f"{base_url.rstrip('/')}/api/generate"
    payload = {
        "model": chosen_model,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        }
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "ShortsVideoCreators"},
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=timeout) as res:
        if res.status != 200:
            raise RuntimeError(f"Ollama API returned HTTP {res.status}")
        body = json.loads(res.read().decode("utf-8"))
        return body.get("response", "").strip()


def get_ollama_openai_client(base_url: str = DEFAULT_OLLAMA_BASE_URL) -> OpenAI:
    """Return an OpenAI-compatible client pointed at local Ollama /v1."""
    v1_url = f"{base_url.rstrip('/')}/v1"
    return OpenAI(
        base_url=v1_url,
        api_key="ollama",  # Ollama doesn't require key, but OpenAI client needs non-empty string
    )
