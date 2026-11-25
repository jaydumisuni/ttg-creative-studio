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
