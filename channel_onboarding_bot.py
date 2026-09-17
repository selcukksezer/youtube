"""
Channel onboarding bot facade — backwards compatibility module.
Delegates to the modular `channel_bot` package.
"""

from channel_bot import (
    parse_channel_url,
    PROFILES_BASE_DIR,
    analyze_channel,
    execute_warmup_session,
    execute_studio_upload,
    ChannelOnboardingBot,
    channel_bot
)

__all__ = [
    "parse_channel_url",
    "PROFILES_BASE_DIR",
    "analyze_channel",
    "execute_warmup_session",
    "execute_studio_upload",
    "ChannelOnboardingBot",
    "channel_bot"
]
