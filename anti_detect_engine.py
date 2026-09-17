"""
Anti-Detection, Session Jitter & Digital Footprint Masking Engine (Facade)
Maintained for 100% backwards-compatibility across all tests and pipeline callers.
All core logic is modularly organized in the `anti_detect/` package:
- anti_detect/profile.py        : BrowserProfile dataclass, user agents, screen resolutions, comments pool
- anti_detect/human_behavior.py : Bezier mouse trajectory, typing delays, upload jitter, warmup routines
- anti_detect/verification.py   : Hardware consistency, proxy checks, DNS leak tests, TLS JA3 tests
- anti_detect/stealth.py        : High-entropy stealth JS injection, Chrome CLI args
- anti_detect/video_noise.py    : MP4 atom size variation and unique hashing
- anti_detect/tls_session.py    : Native Chrome JA3 impersonation session
- anti_detect/engine.py         : AntiDetectEngine coordinator and singleton instance
"""

from anti_detect import (
    BrowserProfile,
    STANDARD_MACOS_FONTS,
    MAC_USER_AGENTS,
    RESOLUTIONS,
    PRE_UPLOAD_NATURAL_COMMENTS,
    AntiDetectEngine,
    anti_detect_engine,
    TlsChromeSession,
    calculate_upload_jitter,
    generate_typing_delays,
    generate_bezier_mouse_path,
    human_mouse_move,
    human_type_text,
    generate_warmup_session_plan,
    generate_pre_upload_interaction_plan,
    calculate_natural_session_duration,
    verify_user_agent_hardware_consistency,
    verify_recovery_email_isolation,
    verify_phone_verification_quality,
    verify_residential_proxy,
    verify_screen_viewport_consistency,
    verify_font_masking,
    verify_http2_http3_support,
    get_residential_network_conditions,
    apply_residential_network_jitter,
    verify_login_location_consistency,
    verify_profile_cache_integrity,
    verify_client_hints,
    test_dns_leak,
    test_tls_ja3_fingerprint,
    apply_video_size_variation,
    generate_stealth_js,
    get_chrome_cli_args,
    __all__,
)
