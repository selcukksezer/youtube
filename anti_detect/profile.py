"""
Browser Profile Dataclass, Presets, Fonts & Resolutions
Covers items: 9, 13, 20, 21
"""
import random
from typing import Optional
from dataclasses import dataclass, field

# Standard macOS font whitelist to cloak font enumeration fingerprinting (Rule 20)
STANDARD_MACOS_FONTS = [
    "-apple-system",
    "BlinkMacSystemFont",
    "SF Pro Text",
    "SF Pro Display",
    "Helvetica",
    "Helvetica Neue",
    "Arial",
    "Monaco",
    "Menlo",
    "Courier",
    "Courier New",
    "Times",
    "Times New Roman",
    "Georgia",
    "Palatino",
    "Trebuchet MS",
    "Verdana",
    "Apple Color Emoji"
]

MAC_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
]

# Rule 21: Strict standard aspect ratio resolutions to prevent window bounds overflow
RESOLUTIONS = [
    (1920, 1080),  # Standard Full HD 16:9
    (1440, 900),   # Standard MacBook 16:10
    (1680, 1050),  # Standard 16:10 Wide
]

# Rule 17: Pre-upload natural comments pool
PRE_UPLOAD_NATURAL_COMMENTS = {
    "tr": [
        "Harika bir tespit, elinize sağlık 🔥",
        "Bunu kaydettim, çok faydalı bilgi 👏",
        "Kesinlikle katılıyorum, devamı gelsin!",
        "Tam aradığım konu, çok net özetlenmiş 👍",
        "Müthiş bakış açısı, tebrikler!",
        "Efsane video olmuş, ellerinize sağlık 🚀"
    ],
    "en": [
        "Really well explained, saved this! 🔥",
        "Spot on perspective, great work 👏",
        "This is so true! Keep it up 👍",
        "Quality content right here!",
        "Super insightful, love this breakdown 🚀"
    ]
}

@dataclass
class BrowserProfile:
    profile_id: str
    user_agent: str
    viewport_width: int
    viewport_height: int
    hardware_concurrency: int
    device_memory: int
    webrtc_policy: str = "disable_non_proxied_udp"
    canvas_noise_seed: float = field(default_factory=lambda: random.uniform(0.0001, 0.0009))
    webgl_vendor: str = "Apple Inc."
    webgl_renderer: str = "Apple M2 Pro"
    audio_noise_jitter: float = field(default_factory=lambda: random.uniform(0.00001, 0.00005))
    accept_language: str = "en-US,en;q=0.9"
    timezone_id: str = "America/New_York"
    proxy_url: Optional[str] = None
