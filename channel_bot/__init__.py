"""
Channel bot package — channel onboarding, anti-detect warmup, and Studio UI uploader.
"""

from .parser import parse_channel_url, PROFILES_BASE_DIR
from .analysis import analyze_channel
from .warmup import execute_warmup_session
from .uploader import execute_studio_upload
from .bot import ChannelOnboardingBot, channel_bot

__all__ = [
    "parse_channel_url",
    "PROFILES_BASE_DIR",
    "analyze_channel",
    "execute_warmup_session",
    "execute_studio_upload",
    "ChannelOnboardingBot",
    "channel_bot"
]
