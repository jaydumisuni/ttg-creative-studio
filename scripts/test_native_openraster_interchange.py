"""PhotoCraft/OpenRaster actual editable-layer roundtrips and rejection checks."""
from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from xml.etree import ElementTree as ET
from zipfile import ZIP_STORED, ZipFile

from PIL import Image

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_openraster_bridge import export_openraster, import_openraster
from ttg_project_schema import CanvasSpec, Layer, TTGProject, Transform


class OpenRasterBridgeTests(unittest.TestCase):
    def test_two_real_alpha_layers_and_multiply_replay_merged_pixels(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            color = Image.new("RGBA", (12, 10), (50, 150, 180, 255))
            color.save(root / "base.png")
            tint = Image.new("RGBA", (7, 6), (220, 95, 200, 180))
            tint.save(root / "overlay.png")
            p = TTGProject(name="PhotoCraft layered interchange", project_type="image")
            p.canvas = CanvasSpec(width=20, height=18, background="#181F36")
            p.layers = [
                Layer(id="bottom", name="Photo background", type="image",
                      transform=Transform(x=1, y=2),
                      properties={"path": "base.png"}),
                Layer(id="top", name="Photo overlay", type="image",
                      transform=Transform(x=6, y=5),
                      properties={"path": "overlay.png", "blend_mode": "multiply"}),
            ]
            original = root / "source.ttgstudio.json"
            p.save(original)
            expected = CanvasRenderer(RenderContext(project_root=root)).render(p)
            ora = root / "photo-interop.ora"
            receipt = export_openraster(p, ora, project_root=root)
            self.assertEqual(receipt.layers, 3)
            with ZipFile(ora) as z:
                self.assertEqual(z.namelist()[0], "mimetype")
                self.assertEqual(z.getinfo("mimetype").compress_type, ZIP_STORED)
                stack = ET.fromstring(z.read("stack.xml")).find("stack")
                self.assertEqual([x.get("name") for x in stack],
                                 ["Photo overlay", "Photo background", "TTG Canvas Background"])
                self.assertEqual(stack[0].get("composite-op"), "svg:multiply")
                with Image.open(z.open("mergedimage.png")) as saved:
                    self.assertEqual(expected.tobytes(), saved.convert("RGBA").tobytes())
            imported_path = root / "photo-reimport.ttgstudio.json"
            importer = import_openraster(ora, imported_path)
            imported = TTGProject.load(imported_path)
            actual = CanvasRenderer(RenderContext(project_root=root)).render(imported)
            self.assertEqual(importer.layers, 3)
            self.assertEqual(expected.tobytes(), actual.tobytes())
            self.assertEqual(imported.layers[-1].properties["blend_mode"], "multiply")
            self.assertEqual(TTGProject.load(original).layers[-1].type, "image")

    def test_unsupported_layers_are_explicitly_rejected_without_writes(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            p = TTGProject()
            p.canvas = CanvasSpec(width=16, height=16)
            p.layers = [Layer(id="unsupported", name="Audio track", type="audio")]
            out = root / "cannot.ora"
            with self.assertRaisesRegex(ValueError, "cannot faithfully"):
                export_openraster(p, out, project_root=root)
            self.assertFalse(out.exists())

    def test_refuse_duplicate_overwrite_and_malicious_or_nested_archive(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            p = TTGProject()
            p.canvas = CanvasSpec(width=8, height=8)
            p.layers = [Layer(id="p", name="pixel", type="shape",
                              properties={"shape": "rectangle", "width": 5, "height": 5})]
            ora = root / "source.ora"
            export_openraster(p, ora, project_root=root)
            with self.assertRaisesRegex(ValueError, "must be a new"):
                export_openraster(p, ora, project_root=root)
            project_path = root / "out.ttgstudio.json"
            import_openraster(ora, project_path)
            with self.assertRaises(FileExistsError):
                import_openraster(ora, project_path)

            zip_path = root / "malicious.ora"
            with ZipFile(zip_path, "w") as archive:
                archive.writestr("mimetype", "image/openraster")
                archive.writestr("stack.xml",
                    '<image w="8" h="8"><stack><layer src="data/../../evil.png" /></stack></image>')
                archive.writestr("data/../../evil.png", b"not-png")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                import_openraster(zip_path, root / "malicious.ttgstudio.json")
            self.assertFalse((root / "evil.png").exists())

            groups = root / "groups.ora"
            with ZipFile(groups, "w") as archive:
                archive.writestr("mimetype", "image/openraster")
                archive.writestr("stack.xml",
                    '<image w="8" h="8"><stack><stack name="group"></stack></stack></image>')
            with self.assertRaisesRegex(ValueError, "Nested groups"):
                import_openraster(groups, root / "groups.ttgstudio.json")

    def test_missing_source_and_unsupported_blending_fail_closed(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            p = TTGProject()
            p.canvas = CanvasSpec(width=8, height=8)
            p.layers = [Layer(id="bad", name="bad", type="image",
                              properties={"path": "absent.png"})]
            with self.assertRaises(FileNotFoundError):
                export_openraster(p, root / "bad.ora", project_root=root)
            p.layers[0].properties["path"] = None
            p.layers[0].properties["blend_mode"] = "overlay"
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                export_openraster(p, root / "bad.ora", project_root=root)


if __name__ == "__main__":
    unittest.main()
