"""
Tests for Chapter 28.19 / Section 2.2 (Madde 19):
reference_repos2/pyJianYingDraft evolution:
- render/keyframe_motion.py: KeyframeProperty, EasingCurve, evaluate_easing, KeyframeTrajectory, build_ffmpeg_cosine_expression
"""

import unittest
from render.keyframe_motion import (
    KeyframeProperty,
    EasingCurve,
    evaluate_easing,
    Keyframe,
    KeyframeTrajectory,
)


class TestPyJianYingDraftKeyframeMotion(unittest.TestCase):
    def test_evaluate_easing_curves(self):
        # Linear
        self.assertAlmostEqual(evaluate_easing(0.0, EasingCurve.LINEAR), 0.0)
        self.assertAlmostEqual(evaluate_easing(0.5, EasingCurve.LINEAR), 0.5)
        self.assertAlmostEqual(evaluate_easing(1.0, EasingCurve.LINEAR), 1.0)

        # Cosine Ease-In-Out
        self.assertAlmostEqual(evaluate_easing(0.0, EasingCurve.COSINE_EASE_IN_OUT), 0.0)
        self.assertAlmostEqual(evaluate_easing(0.5, EasingCurve.COSINE_EASE_IN_OUT), 0.5)
        self.assertAlmostEqual(evaluate_easing(1.0, EasingCurve.COSINE_EASE_IN_OUT), 1.0)

        # Smoothstep
        self.assertAlmostEqual(evaluate_easing(0.0, EasingCurve.SMOOTHSTEP), 0.0)
        self.assertAlmostEqual(evaluate_easing(0.5, EasingCurve.SMOOTHSTEP), 0.5)
        self.assertAlmostEqual(evaluate_easing(1.0, EasingCurve.SMOOTHSTEP), 1.0)

    def test_keyframe_trajectory_interpolation(self):
        traj = KeyframeTrajectory(KeyframeProperty.SCALE)
        traj.add_keyframe(time_sec=0.0, value=1.0, curve=EasingCurve.COSINE_EASE_IN_OUT)
        traj.add_keyframe(time_sec=4.0, value=1.20, curve=EasingCurve.COSINE_EASE_IN_OUT)

        # Boundary checks
        self.assertAlmostEqual(traj.evaluate_at(-1.0), 1.0)
        self.assertAlmostEqual(traj.evaluate_at(0.0), 1.0)
        self.assertAlmostEqual(traj.evaluate_at(4.0), 1.20)
        self.assertAlmostEqual(traj.evaluate_at(10.0), 1.20)

        # Midpoint check (cosine midpoint is exactly 1.10)
        self.assertAlmostEqual(traj.evaluate_at(2.0), 1.10, places=3)

    def test_build_ffmpeg_cosine_expression(self):
        traj = KeyframeTrajectory(KeyframeProperty.SCALE)
        traj.add_keyframe(0.0, 1.0)
        traj.add_keyframe(3.5, 1.15)

        expr = traj.build_ffmpeg_cosine_expression(var_name="t")
        self.assertIn("1.000 + (0.150)", expr)
        self.assertIn("cos(3.14159265", expr)
        self.assertIn("3.500", expr)


if __name__ == "__main__":
    unittest.main()
