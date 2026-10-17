"""Automated contract verification for the 100-item UI/UX improvement roadmap (Categories A-J)."""

from __future__ import annotations

from pathlib import Path

import config

ROOT = Path(config.BASE_DIR)
INDEX_HTML = ROOT / "static" / "index.html"
STUDIO_CSS = ROOT / "static" / "studio.css"
JS_DIR = ROOT / "static" / "js"

UX_MODULES = [
    ("studio-wizard.js", ["setStudioWizardStep", "syncWizardBreadcrumbsAndTicks", "resetCurrentWizardStep"]),
    ("studio-wizard-step1.js", ["btn-wiz-rotate-ideas", "wiz-lang-voice-sync-badge", "btn-wiz-undo-niche-sync"]),
    ("studio-wizard-step2.js", ["wiz-voice-quick-cards", "wiz-voice-speed-tone-bar", "wiz-manuscript-dropzone"]),
    ("studio-wizard-step3.js", ["mockup-watermark-badge", "mockup-split-preview-pill", "syncWizardStep3UI"]),
    ("studio-wizard-step4.js", ["btn-wiz4-auto-repair", "wiz-step4-plain-metrics", "syncRenderEstimator"]),
    ("studio-phone-preview.js", ["wiz-phone-top-controls", "select-phone-device-frame", "btn-phone-safe-zone"]),
    ("timeline-ux-enhancements.js", ["tl-ux-toolbar-group", "btn-tl-undo", "btn-tl-refresh-all-visuals"]),
    ("tools-ux-enhancements.js", ["media-ux-top-wrap", "media-subtabs-bar", "media-favorites-bar"]),
    ("gallery-channels-ux.js", ["header-channel-switcher", "gallery-filter-search-bar", "channels-weekly-calendar"]),
    ("visual-hierarchy-ux.js", ["cmd-palette-modal", "btn-density-toggle", "mobile-preview-drawer-fab"]),
    ("secondary-tabs-ux.js", ["niches-quick-sort-bar", "growth-kpi-hero-strip", "fx-split-ratio-controller"]),
]


def test_all_10_ux_category_modules_exist_and_under_600_lines() -> None:
    """Every Category A-J UX module must exist, be non-empty, and stay <= 600 lines."""
    for filename, expected_tokens in UX_MODULES:
        path = JS_DIR / filename
        assert path.exists(), f"Missing UX module: {filename}"
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()
        assert 50 <= len(lines) <= 600, f"{filename} has {len(lines)} lines (must be <= 600)"
        for token in expected_tokens:
            assert token in content, f"Expected token '{token}' missing in {filename}"


def test_index_html_loads_all_10_ux_category_modules_in_order() -> None:
    """static/index.html must include script tags for all 10 UX modules before app.js."""
    html = INDEX_HTML.read_text(encoding="utf-8")
    app_js_pos = html.find('/static/app.js')
    assert app_js_pos != -1, "static/app.js script tag not found in index.html"

    last_pos = -1
    for filename, _ in UX_MODULES:
        script_ref = f"/static/js/{filename}"
        pos = html.find(script_ref)
        assert pos != -1, f"{script_ref} not linked in static/index.html"
        assert pos < app_js_pos, f"{script_ref} must load before /static/app.js"
        assert pos > last_pos, f"{script_ref} is out of expected load order"
        last_pos = pos


def test_studio_css_defines_styles_for_all_10_ux_categories() -> None:
    """static/studio.css must contain key selectors for Categories A through J."""
    css = STUDIO_CSS.read_text(encoding="utf-8")
    required_selectors = [
        ".wiz-voice-speed-tone-bar",    # Category C
        ".wiz-manuscript-dropzone",     # Category C
        ".wiz-phone-top-controls",      # Category F
        ".tl-ux-toolbar-group",         # Category G
        ".media-subtabs-bar",           # Category H
        ".channels-weekly-calendar",    # Category I
        ".cmd-palette-overlay",         # Category J (91)
        ".shimmer-skeleton",            # Category J (92)
        ".toast-action-btn",            # Category J (93)
        ".is-sticky-stage-rail",        # Category J (94)
        ":focus-visible",               # Category J (95)
        ".sem-badge-ready",             # Category J (96)
        ".ux-floating-tooltip",         # Category J (97)
        ".mobile-preview-drawer-fab",   # Category J (98)
        "body.density-compact",         # Category J (100)
    ]
    for sel in required_selectors:
        assert sel in css, f"Missing CSS selector '{sel}' in static/studio.css"
