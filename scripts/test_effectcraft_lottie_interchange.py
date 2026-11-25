"""EffectCraft Lottie subset interoperability with the genuine donor fixture."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ttg_effectcraft_lottie_bridge import export_lottie, import_lottie
from ttg_project_schema import CanvasSpec, Keyframe, Layer, TTGProject

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/effectcraft_bouncing_ball.json"


class EffectCraftLottieInterop(unittest.TestCase):
    def test_import_actual_donor_lottie_fixture_keeps_motion(self):
        with TemporaryDirectory() as d:
            output = Path(d) / "effectcraft.ttgstudio.json"
            receipt = import_lottie(FIXTURE, output)
            self.assertEqual(receipt["layers"], 1)
            project = TTGProject.load(output)
            self.assertEqual(project.canvas.fps, 30)
            self.assertEqual(project.layers[0].name, "Ball")
            self.assertEqual(project.layers[0].properties["shape"], "ellipse")
            self.assertEqual(project.layers[0].properties["width"], 40)
            self.assertEqual([round(x.time, 4) for x in project.layers[0].keyframes["position"]],
                             [0, 0.5, 1])
            self.assertEqual([x.value[1] for x in project.layers[0].keyframes["position"]],
                             [20, 140, 20])
            self.assertEqual(project.layers[0].keyframes["position"][1].easing["type"],
                             "cubic_bezier")

    def test_export_import_native_animated_shape_and_hold(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            project = TTGProject(name="Movement", project_type="motion")
            project.canvas = CanvasSpec(width=220, height=180, fps=30, duration=2)
            project.layers = [
                Layer(id="shape", name="TTG moving rectangle", type="shape",
                      properties={"shape": "rectangle", "width": 40,
                                  "height": 30, "fill": "#0BE5FF"},
                      keyframes={"position": [
                          Keyframe(0, [10, 20, 0], "linear"),
                          Keyframe(1, [80, 40, 0], "hold"),
                          Keyframe(2, [120, 70, 0],
                                   {"type": "cubic_bezier",
                                    "handles": [0.2, 0.4, 0.7, 1]}),
                      ]}),
            ]
            orig = root / "source.ttgstudio.json"
            project.save(orig)
            lottie = root / "effect.lottie.json"
            exported = export_lottie(project, lottie)
            self.assertEqual(exported["layers"], 1)
            l = json.loads(lottie.read_text())
            self.assertEqual(l["layers"][0]["shapes"][0]["it"][0]["ty"], "rc")
            self.assertEqual(l["layers"][0]["ks"]["p"]["k"][0]["h"], 1)
            result = root / "reopen.ttgstudio.json"
            imported = import_lottie(lottie, result)
            self.assertEqual(imported["layers"], 1)
            reopened = TTGProject.load(result)
            self.assertEqual([kf.value[:2] for kf in reopened.layers[0].keyframes["position"]],
                             [[10, 20], [80, 40], [120, 70]])
            self.assertEqual(reopened.layers[0].keyframes["position"][1].easing, "hold")
            self.assertEqual(TTGProject.load(orig).layers[0].id, "shape")

    def test_nonshape_video_and_effects_refused_without_file(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            project = TTGProject()
            project.layers = [Layer(id="video", name="clip", type="video")]
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                export_lottie(project, root / "no.json")
            project.layers[0] = Layer(id="shape", name="shape", type="shape",
                                      effects=[{"type": "blur"}])
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                export_lottie(project, root / "no.json")
            self.assertFalse((root / "no.json").exists())

    def test_external_assets_rejected_instead_of_silently_dropped(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            doc = json.loads(FIXTURE.read_text())
            doc["assets"] = [{"id": "asset0", "p": "remote.png"}]
            test = root / "assets.json"
            test.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, "assets"):
                import_lottie(test, root / "cannot.ttgstudio.json")
            self.assertFalse((root / "cannot.ttgstudio.json").exists())


if __name__ == "__main__":
    unittest.main()
