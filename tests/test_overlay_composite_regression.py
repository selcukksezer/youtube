"""
Regression: apply_* overlay helpers must assign overlay before CompositeVideoClip.

Catches NameError class fixed in apply_neon_countdown_overlay (Item 212, ac3c1fa1).
"""
import ast
import inspect
import os
import unittest

from moviepy.editor import ColorClip

import config
from effects import overlays as overlays_mod


def _apply_functions_using_overlay_name():
    """Return apply_* names that reference bare `overlay` in CompositeVideoClip."""
    src = inspect.getsource(overlays_mod)
    tree = ast.parse(src)
    found = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or not node.name.startswith("apply_"):
            continue
        uses_overlay = False
        assigns_overlay = False
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and n.id == "overlay":
                if isinstance(n.ctx, ast.Store):
                    assigns_overlay = True
                elif isinstance(n.ctx, ast.Load):
                    uses_overlay = True
        if uses_overlay:
            found.append((node.name, assigns_overlay))
    return found


class TestOverlayCompositeRegression(unittest.TestCase):
    def test_no_apply_function_uses_overlay_without_assignment(self):
        offenders = [name for name, assigned in _apply_functions_using_overlay_name() if not assigned]
        self.assertEqual(
            offenders,
            [],
            f"apply_* functions use `overlay` without assignment: {offenders}",
        )

    def test_post_end_card_overlay_chain_no_name_error(self):
        """Mirror video_composer path: end card → Item 212 → 246 → 138 → 232 → 238 → 235/236."""
        prev = getattr(config, "RENDER_SAFE_MODE", True)
        config.RENDER_SAFE_MODE = False
        try:
            from effects.overlays import (
                apply_bookmark_cta_overlay,
                apply_dynamic_progress_bar,
                apply_end_card_to_video,
                apply_micro_animated_sticker_overlay,
                apply_neon_countdown_overlay,
                apply_neon_curiosity_opening_graphic,
                apply_share_cta_overlay,
                apply_sticky_hook_banner_overlay,
            )

            clip = ColorClip(size=(720, 1280), color=(20, 20, 40), duration=10.0)
            clip.fps = 30
            combined = apply_end_card_to_video(clip, duration=3.0)
            combined = apply_neon_countdown_overlay(combined, duration=3.0, position="top_right")
            combined = apply_neon_curiosity_opening_graphic(combined, duration=2.5, symbol="?")
            combined = apply_dynamic_progress_bar(combined, bar_height=4, position="bottom")
            combined = apply_sticky_hook_banner_overlay(combined, banner_text="REGRESSION")
            combined = apply_micro_animated_sticker_overlay(combined, sticker="arrow", duration=2.5)
            combined = apply_share_cta_overlay(combined, cta_text="share", start_at=2.0, duration=2.0)
            combined = apply_bookmark_cta_overlay(combined, cta_text="save", start_at=4.0, duration=2.0)
            self.assertEqual(combined.duration, 10.0)
            self.assertEqual(combined.size, (720, 1280))
        finally:
            config.RENDER_SAFE_MODE = prev

    def test_apply_overlay_functions_composite_with_render_safe_mode_off(self):
        prev = getattr(config, "RENDER_SAFE_MODE", True)
        config.RENDER_SAFE_MODE = False
        clip = ColorClip(size=(720, 1280), color=(30, 30, 60), duration=5.0)
        clip.fps = 30

        cases = [
            ("apply_neon_countdown_overlay", {"duration": 3.0, "position": "top_right"}),
            ("apply_neon_curiosity_opening_graphic", {"duration": 2.5, "symbol": "?"}),
            ("apply_keyword_white_flash_overlay", {"timestamp": 1.0, "duration": 0.18}),
            ("apply_infinite_spiral_overlay", {"duration": 2.0}),
            ("apply_time_tunnel_overlay", {"duration": 2.0}),
            ("apply_end_card_to_video", {"duration": 2.0}),
            ("apply_ui_element_overlay", {
                "ui_type": "ios_notification",
                "header_text": "Test",
                "body_text": "Body",
                "start_time": 0.5,
                "duration": 2.0,
            }),
            ("apply_dynamic_progress_bar", {"bar_height": 4, "position": "bottom"}),
            ("apply_sticky_hook_banner_overlay", {"banner_text": "HOOK"}),
            ("apply_micro_animated_sticker_overlay", {"sticker": "arrow", "duration": 2.0}),
            ("apply_share_cta_overlay", {"cta_text": "Paylaş", "start_at": 1.0, "duration": 2.0}),
            ("apply_bookmark_cta_overlay", {"cta_text": "Kaydet", "start_at": 2.0, "duration": 2.0}),
            ("apply_hybrid_frame_overlay", {"label": "TEST", "bg_style": "neon"}),
            ("apply_neon_frame_overlay", {}),
            ("apply_epic_vignette_overlay", {}),
            ("apply_soft_vignette_overlay", {}),
            ("apply_countdown_wheel_overlay", {"duration": 2.0}),
            ("apply_eq_bar_overlay", {"duration": 2.0}),
            ("apply_split_choice_overlay", {"header": "SEÇ", "body": "A vs B", "duration": 2.0}),
            ("apply_subtitle_bar_overlay", {"header": "Dizi", "body": "Kelime", "duration": 2.0}),
        ]

        try:
            for func_name, kwargs in cases:
                with self.subTest(func=func_name):
                    fn = getattr(overlays_mod, func_name)
                    out = fn(clip, **kwargs)
                    self.assertEqual(out.size, (720, 1280), func_name)
                    self.assertGreater(out.duration, 0, func_name)
        finally:
            config.RENDER_SAFE_MODE = prev

    def test_video_composer_no_bare_overlay_after_end_card(self):
        composer_path = os.path.join(config.BASE_DIR, "video_composer.py")
        with open(composer_path, encoding="utf-8") as fh:
            src = fh.read()
        # Guard against inline CompositeVideoClip([..., overlay]) without local assignment.
        self.assertNotIn("CompositeVideoClip([combined, overlay]", src)
        self.assertNotIn("CompositeVideoClip([base_clip, overlay]", src)


if __name__ == "__main__":
    unittest.main()
