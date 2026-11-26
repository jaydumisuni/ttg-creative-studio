"""DNG TIFF IFD0 structural evidence regressions; synthetic, not real RAW development."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, main
import struct,sys
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from _synthetic_dng_fixture import write_synthetic_dng
from ttg_lightcraft_raw_bridge import import_developed_raw,_inspect_dng_ifd0
from ttg_project_schema import TTGProject


class DngStructuralValidationTests(TestCase):
    def test_little_endian_dng_ifd_structural_evidence_in_project(self):
        with TemporaryDirectory() as d:
            p=Path(d);raw=p/"camera.dng";write_synthetic_dng(raw)
            developed=p/"developed.png"
            Image.new("RGB",(32,24),(65,95,105)).save(developed)
            dest=p/"registered.ttgstudio.json"
            receipt=import_developed_raw(raw,developed,dest)
            self.assertEqual(receipt["raw_structural_level"],"dng_tiff_ifd0")
            evidence=TTGProject.load(dest).export["lightcraft_raw_handoff"]["raw_structural_evidence"]
            self.assertEqual(evidence["tiff_byte_order"],"II")
            self.assertEqual(evidence["dng_version"],[1,4,0,0])
            self.assertEqual(evidence["declared_dimensions"],[32,24])
            self.assertEqual(evidence["first_ifd_entries"],3)
            self.assertFalse(evidence["raw_pixel_data_decoded"])

    def test_big_endian_still_parses_and_no_camera_claim(self):
        with TemporaryDirectory() as d:
            p=Path(d);raw=p/"camera.dng";write_synthetic_dng(raw,big_endian=True)
            src=_inspect_dng_ifd0(raw,raw.stat().st_size)
            self.assertEqual(src["declared_dimensions"],[32,24])
            self.assertEqual(src["tiff_byte_order"],"MM")
            self.assertFalse(src["raw_pixel_data_decoded"])

    def test_fake_magic_without_dngversion_or_truncated_ifd_denied(self):
        with TemporaryDirectory() as d:
            p=Path(d);raw=p/"forged.dng"
            raw.write_bytes(b"II*\x00"+b"\x00"*64)
            preview=p/"valid.png";Image.new("RGB",(16,16)).save(preview)
            dest=p/"bad.ttgstudio.json"
            with self.assertRaisesRegex(ValueError,"IFD"):
                import_developed_raw(raw,preview,dest)
            self.assertFalse(dest.exists())
            write_synthetic_dng(raw)
            data=bytearray(raw.read_bytes())
            # Remove DNGVersion TIFF tag without invalidating the IFD envelope.
            data[34:36]=struct.pack("<H",50705)
            raw.write_bytes(data)
            with self.assertRaisesRegex(ValueError,"DNGVersion"):
                import_developed_raw(raw,preview,dest)
            self.assertFalse(dest.exists())
            write_synthetic_dng(raw)
            data=bytearray(raw.read_bytes());data[4:8]=struct.pack("<I",len(data)+100)
            raw.write_bytes(data)
            with self.assertRaisesRegex(ValueError,"IFD"):
                import_developed_raw(raw,preview,dest)
            self.assertFalse(dest.exists())

    def test_dng_dimensions_over_budget_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d);raw=p/"too-big.dng";write_synthetic_dng(raw)
            data=bytearray(raw.read_bytes())
            # 256 (width) LONG, value at IFD offset 8+2+8.
            data[18:22]=struct.pack("<I",999999)
            raw.write_bytes(data)
            with self.assertRaisesRegex(ValueError,"dimension"):
                _inspect_dng_ifd0(raw,raw.stat().st_size)


if __name__=="__main__":
    main()
