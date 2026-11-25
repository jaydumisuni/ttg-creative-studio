#!/usr/bin/env python3
"""Native TTG motion curves: donor-reference numeric and real renderer proof.

Uses EffectCraft's independently captured temporal-easing reference values
as a numerical oracle; Studio owns its JSON curve, actions, evaluation and pixels.
"""
from __future__ import annotations

import hashlib
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ttg_action_engine import ActionEngine
from ttg_canvas_engine import RenderContext
from ttg_motion_exporter import MotionExporter
from ttg_project_schema import Keyframe, TTGProject
from ttg_property_engine import evaluate_keyframes
from ttg_timeline_engine import TimelineEngine, ease_value


def cubic(*handles: float) -> dict:
    return {"type": "cubic_bezier", "handles": list(handles)}


class NativeMotionCurveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.timeline = TimelineEngine()

    def test_donor_numeric_reference_overlapping_handles(self) -> None:
        # EffectCraft AE26.3x87 velocity probes: out/in speed=0,
        # each influence=80% of segment duration.
        keys = [Keyframe(0.0, 0.0), Keyframe(1.0, 100.0, cubic(0.8, 0, 0.2, 1))]
        for t, expected in [
            (0.1, 0.59243939036327),
            (0.25, 4.76438030608764),
            (0.4, 18.4284394271562),
            (0.75, 95.2356196939123),
        ]:
            with self.subTest(t=t):
                self.assertAlmostEqual(self.timeline.value_at(keys, t), expected, delta=1e-7)

    def test_asymmetric_velocity_reference(self) -> None:
        # Source AE probe: out speed 20/s at 80% influence, in 80/s at 60%.
        keys = [Keyframe(0, 0), Keyframe(1, 100, cubic(.8, .16, .4, .52))]
        for t, expected in [(0.1, 2.25754942621577), (0.25, 6.99841889412931),
                            (0.4, 14.9334636959052), (0.75, 73.8196785378389)]:
            with self.subTest(t=t):
                self.assertAlmostEqual(self.timeline.value_at(keys, t), expected, delta=1e-7)

    def test_descending_velocity_reference(self) -> None:
        # EffectCraft AE probe: descending 100 to 0, negative speeds.
        keys = [Keyframe(0, 100), Keyframe(1, 0, cubic(.6, .12, .2, .36))]
        for time, expected in [(0.1, 97.6395466334594), (0.25, 91.597048571292),
                               (0.4, 74.5367957474338), (0.75, 22.3789127753126)]:
            with self.subTest(time=time):
                self.assertAlmostEqual(self.timeline.value_at(keys, time), expected, delta=1e-7)

    def test_exact_endpoints_and_midpoint_singularity(self) -> None:
        curve = cubic(1.0, 0.0, 0.0, 1.0)
        self.assertEqual(ease_value(0, curve), 0)
        self.assertEqual(ease_value(1, curve), 1)
        self.assertAlmostEqual(ease_value(.5, curve), .5, places=12)
        for t in (0.5 - 1e-9, 0.5 - 1e-12, 0.5 + 1e-12, 0.5 + 1e-9):
            u = .5 + math.copysign(abs((t - .5) / 4) ** (1/3), t - .5)
            expected = 3*(1-u)*u*u + u*u*u
            self.assertAlmostEqual(ease_value(t, curve), expected, delta=1e-7)

    def test_hold_jumps_at_incoming_key(self) -> None:
        keys = [Keyframe(0, [10, 20]), Keyframe(1, [80, 40], "hold")]
        self.assertEqual(self.timeline.value_at(keys, 0.999), [10, 20])
        self.assertEqual(self.timeline.value_at(keys, 1), [80, 40])
        self.assertEqual(self.timeline.value_at(keys, 0), [10, 20])

    def test_curve_handles_support_overshoot_and_vector(self) -> None:
        self.assertGreater(ease_value(.5, cubic(.3, 2.0, .7, 2.0)), 1)
        values = [Keyframe(0, [0, 20]), Keyframe(1, [100, 120], cubic(.3, 0, .7, 1))]
        self.assertEqual(self.timeline.value_at(values, .5), [50, 70])

    def test_legacy_easing_is_unchanged(self) -> None:
        cases = {
            "linear": .25,
            "ease_in": .0625,
            "ease_out": .4375,
            "ease_in_out": .15625,
        }
        for mode, expected in cases.items():
            with self.subTest(easing=mode):
                self.assertAlmostEqual(ease_value(.25, mode), expected)
        # Keep historical right-key incoming easing semantics.
        keys = [Keyframe(0, 0, "ease_in"), Keyframe(1, 100, "ease_in_out")]
        self.assertAlmostEqual(self.timeline.value_at(keys, .25), 15.625)

    def test_invalid_curve_fails_explicitly(self) -> None:
        cases = [
            {"type": "cubic_bezier", "handles": [0, 0, 1]},
            cubic(-.1, 0, .5, 1),
            cubic(.3, float("nan"), .7, 1),
            cubic(.3, 0, .7, float("inf")),
            {"type": "unknown", "handles": [.3, 0, .7, 1]},
            {"type": "cubic_bezier", "handles": [.3, 0, .7, 1], "ignore": True},
            {"type": "cubic_bezier", "handles": [True, 0, .7, 1]},
        ]
        for curve in cases:
            with self.subTest(curve=curve), self.assertRaises(ValueError):
                ease_value(.5, curve)

    def test_bad_curve_does_not_mutate_project(self) -> None:
        action = ActionEngine()
        project = action.new_project("Fail Closed", "motion")
        layer = action.add_shape(project)
        with self.assertRaises(ValueError):
            action.add_keyframe(project, layer.id, "position", 1, [100, 0, 0],
                                cubic(-.5, 0, .2, 1))
        self.assertEqual(layer.keyframes, {})

    def test_project_roundtrip_and_two_evaluators_agree(self) -> None:
        action = ActionEngine()
        project = action.new_project("Native Motion Curve", "motion")
        layer = action.add_shape(project, x=0, y=0)
        action.add_keyframe(project, layer.id, "position", 0, [0, 0, 0])
        action.add_keyframe(project, layer.id, "position", 1, [120, 60, 0],
                            cubic(.8, 0, .2, 1))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "native-curve.ttgstudio.json"
            project.save(path)
            loaded = TTGProject.load(path)
            self.assertEqual(loaded.layers[0].keyframes["position"][1].easing,
                             cubic(.8, 0, .2, 1))
            expected = self.timeline.value_at(loaded.layers[0].keyframes["position"], .25)
            actual = evaluate_keyframes(loaded, layer.id, "position", .25)
            self.assertEqual(actual, expected)
            self.assertAlmostEqual(
                self.timeline.apply_to_layer(loaded.layers[0], .25).transform.x, expected[0])

    def test_real_canvas_render_differs_from_linear_but_roundtrip_replays(self) -> None:
        action = ActionEngine()
        project = action.new_project("Actual Pixels", "motion")
        project.canvas.width = 180
        project.canvas.height = 90
        project.canvas.fps = 4
        project.canvas.duration = 1
        layer = action.add_shape(project, x=0, y=15)
        layer.properties["width"] = 18
        layer.properties["height"] = 20
        action.add_keyframe(project, layer.id, "position", 0, [0, 15, 0])
        action.add_keyframe(project, layer.id, "position", 1, [120, 15, 0],
                            cubic(.8, 0, .2, 1))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.ttgstudio.json"
            project.save(path)
            loaded = TTGProject.load(path)
            exporter = MotionExporter(RenderContext(Path(tmp)))
            original = exporter.render_frame(project, .25)
            replay = exporter.render_frame(loaded, .25)
            self.assertEqual(hashlib.sha256(original.tobytes()).digest(),
                             hashlib.sha256(replay.tobytes()).digest())
            loaded.layers[0].keyframes["position"][1].easing = "linear"
            linear = exporter.render_frame(loaded, .25)
            self.assertNotEqual(hashlib.sha256(original.tobytes()).digest(),
                                hashlib.sha256(linear.tobytes()).digest())


if __name__ == "__main__":
    unittest.main(verbosity=2)
