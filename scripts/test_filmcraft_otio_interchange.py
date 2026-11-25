"""FilmCraft/OpenTimelineIO real media timeline interchange regression."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from ttg_filmcraft_otio_bridge import export_otio, import_otio
from ttg_project_schema import CanvasSpec, Keyframe, Layer, TTGProject


class FilmCraftInteropTests(unittest.TestCase):
    def test_overlapping_real_sources_and_gap_roundtrip(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            for name in ("source.mp4", "voice.wav"):
                (root / name).write_bytes(b"test-file-stays-original")
            p = TTGProject(name="FilmCraft exchange", project_type="motion")
            p.canvas = CanvasSpec(width=640, height=360, fps=25, duration=8)
            p.layers = [
                Layer(id="a", type="video", name="video track",
                      properties={"path": "source.mp4", "start": 1.0,
                                  "source_in": 0.5, "source_out": 2.5, "speed": 1.0},
                      keyframes={"opacity": [Keyframe(0, 1)]}),
                Layer(id="b", type="audio", name="audio track",
                      properties={"path": "voice.wav", "start": 0.0,
                                  "duration": 3.0}),
            ]
            project_path = root / "source.ttgstudio.json"
            p.save(project_path)
            output = root / "timeline.otio"
            receipt = export_otio(p, output, project_root=root)
            self.assertEqual(receipt["tracks"], 2)
            self.assertTrue(any("keyframes" in warning for warning in receipt["warnings"]))
            doc = json.loads(output.read_text())
            self.assertEqual(doc["OTIO_SCHEMA"], "Timeline.1")
            self.assertEqual([x["kind"] for x in doc["tracks"]["children"]], ["Video", "Audio"])
            self.assertEqual(len(doc["tracks"]["children"][0]["children"]), 2)
            self.assertEqual(doc["tracks"]["children"][0]["children"][1]["media_reference"]["OTIO_SCHEMA"],
                             "ExternalReference.1")
            imported_path = root / "roundtrip.ttgstudio.json"
            import_otio(output, imported_path)
            result = TTGProject.load(imported_path)
            self.assertEqual(len(result.layers), 2)
            self.assertEqual(result.layers[0].properties["start"], 1.0)
            self.assertEqual(result.layers[0].properties["source_in"], 0.5)
            self.assertEqual(result.layers[0].properties["source_out"], 2.5)
            self.assertEqual(result.layers[0].keyframes["opacity"][0].value, 1)
            self.assertEqual(result.layers[1].properties["duration"], 3.0)
            self.assertEqual(TTGProject.load(project_path).layers[0].properties["path"], "source.mp4")
            with self.assertRaises(FileExistsError):
                import_otio(output, imported_path)

    def test_unsupported_retime_and_missing_real_file_refused(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "clip.mp4").write_bytes(b"actual-file")
            p = TTGProject()
            p.layers = [Layer(id="clip", type="video", name="clip",
                              properties={"path": "clip.mp4", "start": 0,
                                          "source_in": 0, "source_out": 2, "speed": 2})]
            with self.assertRaisesRegex(ValueError, "retime"):
                export_otio(p, root / "no.otio", project_root=root)
            self.assertFalse((root / "no.otio").exists())
            p.layers[0].properties["speed"] = 1
            p.layers[0].properties["path"] = "missing.mp4"
            with self.assertRaises(FileNotFoundError):
                export_otio(p, root / "no.otio", project_root=root)

    def test_complex_filmcraft_metadata_cannot_be_silently_dropped(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "clip.mp4").write_bytes(b"actual-file")
            p = TTGProject()
            p.layers = [Layer(id="c", type="video", name="c",
                              properties={"path": "clip.mp4", "start": 0,
                                          "source_in": 0, "source_out": 2, "speed": 1})]
            export_otio(p, root / "valid.otio", project_root=root)
            doc = json.loads((root / "valid.otio").read_text())
            children = doc["tracks"]["children"][0]["children"]
            children[0]["effects"] = [{"OTIO_SCHEMA": "Effect.1", "name": "unmapped"}]
            edited = root / "advanced.otio"
            edited.write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, "effects"):
                import_otio(edited, root / "not-created.ttgstudio.json")
            self.assertFalse((root / "not-created.ttgstudio.json").exists())

    def test_external_file_scheme_only(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "clip.mp4").write_bytes(b"actual-file")
            p = TTGProject()
            p.layers = [Layer(id="c", type="video", name="c",
                              properties={"path": "clip.mp4", "start": 0,
                                          "source_in": 0, "source_out": 2, "speed": 1})]
            export_otio(p, root / "valid.otio", project_root=root)
            doc = json.loads((root / "valid.otio").read_text())
            doc["tracks"]["children"][0]["children"][0]["media_reference"]["target_url"] = "https://example.com/untrusted.mp4"
            (root / "bad.otio").write_text(json.dumps(doc))
            with self.assertRaisesRegex(ValueError, "local file URL"):
                import_otio(root / "bad.otio", root / "bad.ttgstudio.json")

    def test_no_disguised_non_media_project_as_complete_filmcraft_interchange(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            p = TTGProject()
            p.layers = [Layer(id="label", type="text", name="label")]
            with self.assertRaisesRegex(ValueError, "No media"):
                export_otio(p, root / "empty.otio", project_root=root)


if __name__ == "__main__":
    unittest.main()
