#!/usr/bin/env python3
"""PhotoCraft-informed alpha/blend behavior tested through TTG's real canvas.

The blending implementation is native and original. Assertions are based on
standard W3C/PDF source-over formulas and PhotoCraft's blend reference cases.
"""
from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from ttg_action_engine import ActionEngine
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_project_schema import TTGProject


def scene(background="#808080", foreground="#808080", mode="normal"):
    action = ActionEngine()
    p = action.new_project("TTG Native Layer Blend", "image")
    p.canvas.width, p.canvas.height = 24, 24
    p.canvas.background = background
    layer = action.add_shape(p, "rectangle", x=4, y=4)
    layer.properties.update(width=10, height=10, fill=foreground, blend_mode=mode)
    return p


class NativeLayerBlendTests(unittest.TestCase):
    def render(self, project, root=ROOT):
        return CanvasRenderer(RenderContext(root)).render(project)

    def test_photo_reference_multiply_and_screen(self):
        # PhotoCraft reference for 0.5*0.5=0.25 and Screen(0.5,0.5)=0.75.
        expected = {"multiply": 64, "screen": 192}
        for mode, result in expected.items():
            with self.subTest(mode=mode):
                image = self.render(scene(mode=mode))
                self.assertEqual(image.getpixel((6, 6)), (result, result, result, 255))
                self.assertEqual(image.getpixel((20, 20)), (128, 128, 128, 255))

    def test_normal_legacy_path_still_source_over(self):
        project = scene(mode="normal")
        project.layers[0].properties.pop("blend_mode")
        old = self.render(project)
        project.layers[0].properties["blend_mode"] = "normal"
        new = self.render(project)
        self.assertEqual(old.tobytes(), new.tobytes())
        self.assertEqual(new.getpixel((6, 6)), (128, 128, 128, 255))

    def test_half_transparent_foreground(self):
        for mode, expected in [("multiply", 96), ("screen", 160)]:
            with self.subTest(mode=mode):
                image = self.render(scene(foreground="#80808080", mode=mode))
                pixel = image.getpixel((6, 6))
                self.assertTrue(all(abs(v - expected) <= 1 for v in pixel[:3]), pixel)
                self.assertEqual(pixel[3], 255)

    def test_transparent_backdrop_preserves_source(self):
        for mode in ["multiply", "screen"]:
            with self.subTest(mode=mode):
                pixel = self.render(scene(background="#00000000",
                                          foreground="#80808080", mode=mode)).getpixel((6, 6))
                self.assertEqual(pixel, (128, 128, 128, 128))

    def test_partial_backdrop_and_source_follow_source_over_formula(self):
        sa = da = 128/255
        cb = cs = 128/255
        for mode in ("multiply", "screen"):
            b = cb*cs if mode == "multiply" else cb+cs-cb*cs
            oa = sa + da*(1-sa)
            oc = ((1-sa)*da*cb + sa*((1-da)*cs + da*b))/oa
            pixel = self.render(scene(background="#80808080", foreground="#80808080",
                                      mode=mode)).getpixel((6,6))
            self.assertLessEqual(abs(pixel[0] - round(oc*255)), 2, pixel)
            self.assertLessEqual(abs(pixel[3] - round(oa*255)), 1, pixel)

    def test_unsupported_blends_fail_not_silent_substitute(self):
        for mode in ("overlay", "color_dodge", {}, None, []):
            with self.subTest(mode=mode):
                project = scene()
                project.layers[0].properties["blend_mode"] = mode
                with self.assertRaises(ValueError):
                    self.render(project)

    def test_real_image_layer_and_project_replay(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            asset = root/"asset.png"
            Image.new("RGBA", (5,5), (128,128,128,128)).save(asset)
            action = ActionEngine()
            project = action.new_project("Layer Blend Saved", "image")
            project.canvas.background = "#808080"
            project.canvas.width,project.canvas.height = 12,12
            image_layer = action.add_image(project, "asset.png", x=2, y=2)
            image_layer.properties["blend_mode"] = "multiply"
            src = self.render(project,root)
            self.assertTrue(all(abs(c-96)<=1 for c in src.getpixel((3,3))[:3]))
            path = root/"project.ttgstudio.json"
            project.save(path)
            restored = TTGProject.load(path)
            self.assertEqual(restored.layers[0].properties["blend_mode"], "multiply")
            replay = self.render(restored,root)
            self.assertEqual(hashlib.sha256(src.tobytes()).hexdigest(),
                             hashlib.sha256(replay.tobytes()).hexdigest())

    def test_no_donor_brand_or_new_file_format(self):
        project = scene(mode="multiply")
        stored = project.to_dict()
        self.assertEqual(stored["layers"][0]["properties"]["blend_mode"], "multiply")
        self.assertEqual(project.version,"0.1.0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
