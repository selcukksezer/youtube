"""
Anti-Detect Package
Modularized anti-detection, behavioral emulation, network verification, and browser fingerprint isolation.
"""
from .profile import (
    BrowserProfile,
    STANDARD_MACOS_FONTS,
    MAC_USER_AGENTS,
    RESOLUTIONS,
    PRE_UPLOAD_NATURAL_COMMENTS,
)
from .human_behavior import (
    calculate_upload_jitter,
    generate_typing_delays,
    generate_bezier_mouse_path,
    human_mouse_move,
    human_type_text,
    generate_warmup_session_plan,
    generate_pre_upload_interaction_plan,
    calculate_natural_session_duration,
)
from .verification import (
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
)
from .stealth import (
    generate_stealth_js,
    get_chrome_cli_args,
)
from .video_noise import (
    apply_video_size_variation,
)
from .tls_session import (
    TlsChromeSession,
)
from .engine import (
    AntiDetectEngine,
    anti_detect_engine,
)
from .post_render import (
    apply_post_render_humanization,
)

__all__ = [
    "BrowserProfile",
    "STANDARD_MACOS_FONTS",
    "MAC_USER_AGENTS",
    "RESOLUTIONS",
    "PRE_UPLOAD_NATURAL_COMMENTS",
    "AntiDetectEngine",
    "anti_detect_engine",
    "TlsChromeSession",
    "calculate_upload_jitter",
    "generate_typing_delays",
    "generate_bezier_mouse_path",
    "human_mouse_move",
    "human_type_text",
    "generate_warmup_session_plan",
    "generate_pre_upload_interaction_plan",
    "calculate_natural_session_duration",
    "verify_user_agent_hardware_consistency",
    "verify_recovery_email_isolation",
    "verify_phone_verification_quality",
    "verify_residential_proxy",
    "verify_screen_viewport_consistency",
    "verify_font_masking",
    "verify_http2_http3_support",
    "get_residential_network_conditions",
    "apply_residential_network_jitter",
    "verify_login_location_consistency",
    "verify_profile_cache_integrity",
    "verify_client_hints",
    "test_dns_leak",
    "test_tls_ja3_fingerprint",
    "apply_video_size_variation",
    "generate_stealth_js",
    "get_chrome_cli_args",
    "apply_post_render_humanization",
]
