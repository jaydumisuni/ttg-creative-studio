"""Real exported-PNG PBR set intake and fail-closed provenance validation."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ttg_material_texture_bridge import import_pbr_export_maps
from ttg_project_schema import TTGProject


def fixture(root: Path):
    exported = root / "materialcraft-export"
    exported.mkdir()
    records = {}
    for channel, rgba, cs in (
        ("base_color", (150, 100, 60, 255), "srgb"),
        ("normal", (128, 128, 255, 255), "linear"),
        ("roughness", (100, 100, 100, 255), "linear"),
        ("metallic", (20, 20, 20, 255), "linear"),
    ):
        path = exported / f"{channel}.png"
        Image.new("RGBA", (32, 32), rgba).save(path)
        records[channel] = {
            "path": path.name,
            "colorspace": cs,
            "sha256": sha256(path.read_bytes()).hexdigest(),
        }
    manifest = exported / "mapset.json"
    manifest.write_text(json.dumps({
        "schema": "ttg.studio.pbr-export-mapset.v1",
        "normal_y": "opengl", "channels": records,
    }))
    return exported, manifest


class MaterialTextureInterop(unittest.TestCase):
    def test_four_actual_export_maps_keep_hashes_and_colorspace(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            source, manifest = fixture(root)
            output = root / "asset.ttgstudio.json"
            receipt = import_pbr_export_maps(
                source, manifest, output, material_name="Worn metal"
            )
            self.assertEqual(receipt["asset_count"], 4)
            self.assertFalse(receipt["native_material_graph_imported"])
            project = TTGProject.load(output)
            self.assertEqual(len(project.assets), 4)
            pbr = project.export["pbr_materials"][0]
            self.assertEqual(pbr["normal_y"], "opengl")
            self.assertEqual(pbr["channels"]["normal"]["colorspace"], "linear")
            for channel, item in pbr["channels"].items():
                self.assertEqual(sha256((root / item["path"]).read_bytes()).hexdigest(),
                                 item["sha256"])
                self.assertEqual((source / (channel + ".png")).read_bytes(),
                                 (root / item["path"]).read_bytes())
            with self.assertRaises(FileExistsError):
                import_pbr_export_maps(source, manifest, output, material_name="Worn metal")

    def test_lit_swatch_is_actual_editable_canvas_layer_and_deterministic(self):
        from ttg_canvas_engine import CanvasRenderer, RenderContext
        with TemporaryDirectory() as d:
            root=Path(d)
            source,manifest=fixture(root)
            first=root/"first.ttgstudio.json"
            second=root/"second.ttgstudio.json"
            one=import_pbr_export_maps(source,manifest,first,material_name="Steel")
            two=import_pbr_export_maps(source,manifest,second,material_name="Steel")
            self.assertTrue(one["fixed_light_swatch_rendered"])
            self.assertFalse(one["material_surface_render_verified"])
            p=TTGProject.load(first)
            self.assertEqual(len(p.assets),4)
            self.assertEqual(len(p.layers),1)
            self.assertEqual(p.layers[0].type,"image")
            preview=root/p.layers[0].properties["path"]
            self.assertTrue(preview.is_file())
            self.assertEqual(sha256(preview.read_bytes()).hexdigest(),one["preview_sha256"])
            self.assertEqual(one["preview_sha256"],two["preview_sha256"])
            from PIL import Image
            with Image.open(preview) as pixels:
                rgba=pixels.convert("RGBA")
                self.assertEqual(rgba.size,(32,32))
                self.assertNotEqual(rgba.getpixel((0,0))[:3],(150,100,60))
                merged=CanvasRenderer(RenderContext(project_root=root)).render(p)
                self.assertEqual(merged.convert("RGBA").getpixel((0,0)),rgba.getpixel((0,0)))
            self.assertFalse(p.export["pbr_materials"][0]["mesh_uv_shader_certified"])

    def test_normal_y_and_roughness_change_real_swatch_pixels(self):
        from PIL import Image
        with TemporaryDirectory() as d:
            root=Path(d)
            source,manifest=fixture(root)
            Image.new("RGBA",(32,32),(180,36,240,255)).save(source/"normal.png")
            declaration=json.loads(manifest.read_text())
            declaration["channels"]["normal"]["sha256"]=sha256(
                (source/"normal.png").read_bytes()).hexdigest()
            manifest.write_text(json.dumps(declaration))
            a=import_pbr_export_maps(source,manifest,root/"opengl.ttgstudio.json",
                                     material_name="OpenGL")
            declaration["normal_y"]="directx"
            manifest.write_text(json.dumps(declaration))
            b=import_pbr_export_maps(source,manifest,root/"directx.ttgstudio.json",
                                     material_name="DirectX")
            self.assertNotEqual(a["preview_sha256"],b["preview_sha256"])
            Image.new("RGBA",(32,32),(245,245,245,255)).save(source/"roughness.png")
            declaration["channels"]["roughness"]["sha256"]=sha256(
                (source/"roughness.png").read_bytes()).hexdigest()
            manifest.write_text(json.dumps(declaration))
            c=import_pbr_export_maps(source,manifest,root/"rough.ttgstudio.json",
                                     material_name="Rough")
            self.assertNotEqual(b["preview_sha256"],c["preview_sha256"])

    def test_mismatched_color_space_and_hashes_refused_without_assets(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            source, manifest = fixture(root)
            declaration = json.loads(manifest.read_text())
            declaration["channels"]["normal"]["colorspace"] = "srgb"
            manifest.write_text(json.dumps(declaration))
            with self.assertRaisesRegex(ValueError, "linear color"):
                import_pbr_export_maps(source, manifest, root / "fail.ttgstudio.json",
                                       material_name="Worn metal")
            self.assertFalse((root / "fail_pbr").exists())
            declaration["channels"]["normal"]["colorspace"] = "linear"
            declaration["channels"]["roughness"]["sha256"] = "0" * 64
            manifest.write_text(json.dumps(declaration))
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                import_pbr_export_maps(source, manifest, root / "fail.ttgstudio.json",
                                       material_name="Worn metal")

    def test_symlink_path_traversal_and_native_graph_are_not_smuggled(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            source, manifest = fixture(root)
            declaration = json.loads(manifest.read_text())
            declaration["channels"]["normal"]["path"] = "../escape.png"
            manifest.write_text(json.dumps(declaration))
            with self.assertRaisesRegex(ValueError, "relative PNG"):
                import_pbr_export_maps(source, manifest, root / "fail.ttgstudio.json",
                                       material_name="Worn metal")
            declaration["channels"]["normal"]["path"] = "normal.png"
            manifest.write_text(json.dumps(declaration))
            target = source / "normal.png"
            target.unlink()
            target.symlink_to(source / "base_color.png")
            with self.assertRaisesRegex(ValueError, "unavailable"):
                import_pbr_export_maps(source, manifest, root / "fail.ttgstudio.json",
                                       material_name="Worn metal")


if __name__ == "__main__":
    unittest.main()
