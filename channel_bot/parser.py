"""
Channel URL parsing and isolated profile paths.
"""
import os
import re
from typing import Dict
import config

PROFILES_BASE_DIR = os.path.join(config.BASE_DIR, "tokens", "browser_profiles")
os.makedirs(PROFILES_BASE_DIR, exist_ok=True)


def parse_channel_url(raw_url: str) -> Dict[str, str]:
    """Extracts handle, channel_id, and canonical URL from user input."""
    cleaned = raw_url.strip()
    handle = ""
    channel_id = ""

    # Check @handle
    if "@" in cleaned:
        match = re.search(r"@([A-Za-z0-9_\-\.]+)", cleaned)
        if match:
            handle = f"@{match.group(1)}"
    elif "channel/" in cleaned:
        match = re.search(r"channel/([A-Za-z0-9_\-]+)", cleaned)
        if match:
            channel_id = match.group(1)
            handle = f"channel_{channel_id[:8]}"
    else:
        # Simple string provided
        cleaned_handle = re.sub(r"[^A-Za-z0-9_\-\.]", "", cleaned)
        handle = f"@{cleaned_handle}" if cleaned_handle else "@yenikanal"

    if not handle and not channel_id:
        handle = "@yenikanal"

    canonical_url = f"https://www.youtube.com/{handle}" if handle else f"https://www.youtube.com/channel/{channel_id}"
    slug = handle.lstrip("@").replace(".", "_").lower()

    return {
        "raw_input": raw_url,
        "handle": handle,
        "channel_id": channel_id or slug,
        "profile_id": f"prof_{slug}",
        "canonical_url": canonical_url
    }
