"""
Channel onboarding bot coordinator.
"""
from typing import Dict, List, Any, Optional
from anti_detect_engine import anti_detect_engine
from .parser import parse_channel_url, PROFILES_BASE_DIR
from .analysis import analyze_channel
from .warmup import execute_warmup_session
from .uploader import execute_studio_upload


class ChannelOnboardingBot:
    """Manages channel health analysis, 5-rule compliance checklist, and automated sessions."""

    def __init__(self):
        self.engine = anti_detect_engine

    def parse_channel_url(self, raw_url: str) -> Dict[str, str]:
        """Extracts handle, channel_id, and canonical URL from user input."""
        return parse_channel_url(raw_url)

    def analyze_channel(
        self,
        channel_url: str,
        proxy_url: Optional[str] = None,
        niche: str = "Stoic / Motivasyon",
        is_brand_new: bool = True,
        recovery_email: Optional[str] = None,
        phone_number: Optional[str] = None,
        phone_type: str = "physical"
    ) -> Dict[str, Any]:
        """
        Main analysis function.
        Generates comprehensive channel health diagnostic and 'Neler Yapılması Gerektiği' checklist
        covering Rules 1 to 15.
        """
        return analyze_channel(
            engine=self.engine,
            channel_url=channel_url,
            proxy_url=proxy_url,
            niche=niche,
            is_brand_new=is_brand_new,
            recovery_email=recovery_email,
            phone_number=phone_number,
            phone_type=phone_type
        )

    async def execute_warmup_session(self, channel_id_or_url: str, log_callback=None) -> Dict[str, Any]:
        """
        Executes automated organic warm-up session using Playwright stealth automation.
        Simulates watching Shorts, human Bezier mouse movements, and saves session cookies.
        """
        return await execute_warmup_session(self.engine, channel_id_or_url, log_callback=log_callback)

    def execute_studio_upload(
        self,
        channel_id_or_url: str,
        video_path: str,
        title: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        scheduled_hour: int = 18,
        log_callback=None
    ) -> Dict[str, Any]:
        """
        Executes safe YouTube Studio upload honoring Rules 1, 8, 29:
        - Manipulates file ctime/mtime 20-35 mins in past (Rule 29)
        - Applies schedule jitter (Rule 8)
        - Employs humanized typing delays (Rule 12)
        - Uses isolated profile and anti-detect flags
        """
        return execute_studio_upload(
            self.engine,
            channel_id_or_url=channel_id_or_url,
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            scheduled_hour=scheduled_hour,
            log_callback=log_callback
        )


# Global Bot Instance
channel_bot = ChannelOnboardingBot()
