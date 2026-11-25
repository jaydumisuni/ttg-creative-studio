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
            # Audio must reach the existing Studio MP4 mix path.
            self.assertEqual(len(result.audio_markers), 1)
            self.assertEqual(result.audio_markers[0]["duration"], 3.0)
            self.assertEqual(result.audio_markers[0]["start"], 0.0)
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

    def test_existing_studio_audio_marker_uses_real_native_mix_path(self):
        import wave
        from PIL import Image
        with TemporaryDirectory() as d:
            root = Path(d)
            Image.new("RGB", (20, 16), (20, 150, 90)).save(root / "frame.png")
            audio = root / "voice.wav"
            with wave.open(str(audio), "wb") as wave_file:
                wave_file.setnchannels(1)
                wave_file.setsampwidth(2)
                wave_file.setframerate(8000)
                wave_file.writeframes(b"\\x00\\x00" * 8000)
            project = TTGProject(name="real Studio audio", project_type="motion")
            project.canvas = CanvasSpec(width=320, height=180, fps=30, duration=5)
            project.layers = [
                Layer(id="still", type="image", name="still",
                      properties={"path": "frame.png", "duration": 5})
            ]
            project.audio_markers = [
                {"path": "voice.wav", "start": 1, "source_in": 0,
                 "duration": 1.0, "volume": 0.7}
            ]
            out = root / "with-real-audio.otio"
            receipt = export_otio(project, out, project_root=root)
            self.assertEqual(receipt["tracks"], 2)
            document = json.loads(out.read_text())
            self.assertEqual(document["tracks"]["children"][1]["kind"], "Audio")
            target = root / "replayed.ttgstudio.json"
            import_otio(out, target)
            replayed = TTGProject.load(target)
            self.assertEqual(len(replayed.layers), 1)
            self.assertEqual(len(replayed.audio_markers), 1)
            self.assertEqual(replayed.audio_markers[0]["volume"], 0.7)
            self.assertEqual(replayed.audio_markers[0]["start"], 1.0)
            self.assertEqual(Path(replayed.audio_markers[0]["path"]).read_bytes(),
                             audio.read_bytes())
            from ttg_motion_exporter import MotionExporter
            from ttg_canvas_engine import RenderContext
            args, filters, label = MotionExporter(RenderContext(root))._audio_inputs(replayed)
            self.assertEqual(args[-1], str(audio))
            self.assertEqual(label, "[aout]")
            self.assertTrue(any("volume=0.700" in x for x in filters))
            again = root / "second-pass.otio"
            receipt_again = export_otio(replayed, again, project_root=root)
            self.assertEqual(receipt_again["tracks"], 2)

    def test_filmcraft_private_metadata_refuses_silent_drop(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / "clip.mp4").write_bytes(b"metadata-path-probe-only")
            project = TTGProject()
            project.layers = [
                Layer(id="c", type="video", name="clip",
                      properties={"path": "clip.mp4", "start": 0,
                                  "source_in": 0, "source_out": 2, "speed": 1})
            ]
            export_otio(project, root / "minimal.otio", project_root=root)
            document = json.loads((root / "minimal.otio").read_text())
            document["tracks"]["children"][0]["children"][0].setdefault(
                "metadata", {})["filmcraft"] = {"clip_color_grade": {"unmapped": True}}
            (root / "advanced.otio").write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, "FilmCraft clip metadata"):
                import_otio(root / "advanced.otio", root / "should-not-exist.ttgstudio.json")
            self.assertFalse((root / "should-not-exist.ttgstudio.json").exists())

    def test_no_disguised_non_media_project_as_complete_filmcraft_interchange(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            p = TTGProject()
            p.layers = [Layer(id="label", type="text", name="label")]
            with self.assertRaisesRegex(ValueError, "No media"):
                export_otio(p, root / "empty.otio", project_root=root)


if __name__ == "__main__":
    unittest.main()
