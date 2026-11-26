"""Developed-RAW intake and explicit LightCraft CLI invocation regressions."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
import hashlib
import os
import sys

from PIL import Image
from _synthetic_dng_fixture import write_synthetic_dng

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ttg_lightcraft_raw_bridge import import_developed_raw, develop_with_lightcraft
from ttg_project_schema import TTGProject
from ttg_canvas_engine import CanvasRenderer, RenderContext


class LightCraftRawHandoffTests(TestCase):
    def fixture(self, root):
        raw = root / "camera.dng"
        write_synthetic_dng(raw)
        image = root / "lightcraft-export.png"
        Image.new("RGB",(20,16),(33,103,203)).save(image)
        return raw,image

    def test_rendered_raw_preview_ingested_as_real_editable_pixels(self):
        with TemporaryDirectory() as d:
            root=Path(d);raw,png=self.fixture(root)
            original=raw.read_bytes();render=png.read_bytes()
            dest=root/"editable.ttgstudio.json"
            receipt=import_developed_raw(raw,png,dest)
            self.assertFalse(receipt["actual_raw_decode_certified"])
            project=TTGProject.load(dest)
            self.assertEqual(len(project.assets),1)
            self.assertEqual(project.canvas.width,20)
            self.assertEqual(project.canvas.height,16)
            self.assertEqual(project.layers[0].type,"image")
            self.assertEqual(project.export["lightcraft_raw_handoff"]["raw_source_sha256"],
                             hashlib.sha256(raw.read_bytes()).hexdigest())
            self.assertFalse(project.export["lightcraft_raw_handoff"]["selected_executable_invoked"])
            rendered=CanvasRenderer(RenderContext(root)).render(project)
            self.assertEqual(rendered.getpixel((0,0))[:3], (33,103,203))
            self.assertEqual(raw.read_bytes(), original)
            self.assertEqual(png.read_bytes(), render)
            with self.assertRaises(FileExistsError):
                import_developed_raw(raw,png,dest)

    def test_wrong_raw_signature_and_unsupported_output_rejected(self):
        with TemporaryDirectory() as d:
            root=Path(d);raw,png=self.fixture(root)
            raw.write_bytes(b"not a raw file" + b"a"*80)
            with self.assertRaisesRegex(ValueError,"header"):
                import_developed_raw(raw,png,root/"bad.ttgstudio.json")
            self.assertFalse((root/"bad.ttgstudio.json").exists())
            write_synthetic_dng(raw)
            Image.new("L",(8,8),50).save(png)
            with self.assertRaisesRegex(ValueError,"RGB or RGBA"):
                import_developed_raw(raw,png,root/"bad.ttgstudio.json")

    def test_cli_missing_never_claims_development(self):
        with TemporaryDirectory() as d:
            root=Path(d);raw,png=self.fixture(root)
            with self.assertRaises(FileNotFoundError):
                develop_with_lightcraft(raw,root/"bad.ttgstudio.json",
                                        lightcraft_cli=root/"no-lightcraft-cli")
            self.assertFalse((root/"bad.ttgstudio.json").exists())

    def test_real_argv_command_receipt_through_selected_test_executable(self):
        if os.name == "nt":
            self.skipTest("POSIX executable fixture; real PNG intake remains cross-platform")
        with TemporaryDirectory() as d:
            root=Path(d);raw,png=self.fixture(root)
            binary=root/"lightcraft-test-cli"
            binary.write_text(
                "#!/usr/bin/env python3\n"
                "from PIL import Image\nimport sys\n"
                "assert sys.argv[1]=='render' and sys.argv[3]=='-o'\n"
                "Image.new('RGB',(24,12),(80,90,100)).save(sys.argv[4])\n"
            )
            binary.chmod(0o700)
            out=root/"developed.ttgstudio.json"
            receipt=develop_with_lightcraft(raw,out,lightcraft_cli=binary,exposure=0.2)
            p=TTGProject.load(out)
            self.assertEqual(p.canvas.width,24)
            self.assertEqual(p.canvas.height,12)
            self.assertEqual(p.export["lightcraft_raw_handoff"]["lightcraft_executable_sha256"],
                             hashlib.sha256(binary.read_bytes()).hexdigest())
            self.assertTrue(p.export["lightcraft_raw_handoff"]["selected_executable_invoked"])
            self.assertEqual(receipt["original_raw_sha256"],hashlib.sha256(raw.read_bytes()).hexdigest())
            self.assertFalse(receipt["actual_raw_decode_certified"])


if __name__=="__main__":
    main()
