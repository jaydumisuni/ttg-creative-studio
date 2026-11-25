"""SoundCraft-style native audio gain/fade source and FFmpeg execution contracts."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
import wave
import math
import struct
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from ttg_motion_exporter import MotionExporter
from ttg_canvas_engine import RenderContext
from ttg_project_schema import TTGProject,CanvasSpec
from ttg_filmcraft_otio_bridge import export_otio,import_otio


def real_wave(path):
    with wave.open(str(path),"wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(8000)
        raw=b"".join(struct.pack("<h",round(12000*math.sin(2*math.pi*440*i/8000)))
                     for i in range(12000))
        out.writeframes(raw)


class NativeAudioFades(unittest.TestCase):
    def test_real_source_trim_gain_fades_then_timeline_delay(self):
        with TemporaryDirectory() as t:
            root=Path(t)
            tone=root/"tone.wav"
            real_wave(tone)
            p=TTGProject(name="SoundCraft fade proof",project_type="motion")
            p.canvas=CanvasSpec(width=32,height=24,duration=4,fps=25)
            p.audio_markers=[{"path":"tone.wav","source_in":.1,"start":.3,
                              "duration":1.,"volume":.7,"fade_in":.2,"fade_out":.3}]
            args,filters,label=MotionExporter(RenderContext(root))._audio_inputs(p)
            self.assertEqual(args,["-i",str(tone)])
            self.assertEqual(label,"[aout]")
            self.assertEqual(len(filters),2)
            self.assertIn("atrim=start=0.100:duration=1.000",filters[0])
            self.assertIn("volume=0.700,afade=t=in:st=0:d=0.200",filters[0])
            self.assertIn("afade=t=out:st=0.700:d=0.300",filters[0])
            self.assertIn("adelay=300:all=1",filters[0])
            self.assertTrue(filters[0].index("volume=")<filters[0].index("afade=t=in")<
                            filters[0].index("afade=t=out")<filters[0].index("adelay="))

    def test_unchanged_existing_audio_when_fades_not_requested(self):
        with TemporaryDirectory() as t:
            root=Path(t)
            real_wave(root/"tone.wav")
            p=TTGProject()
            p.audio_markers=[{"path":"tone.wav","start":0,"duration":.6,"volume":1}]
            args,filters,label=MotionExporter(RenderContext(root))._audio_inputs(p)
            self.assertNotIn("afade",filters[0])
            self.assertIn("volume=1.000,adelay=0:all=1",filters[0])

    def test_negative_nonfinite_and_overlong_fades_rejected(self):
        with TemporaryDirectory() as t:
            root=Path(t)
            real_wave(root/"tone.wav")
            p=TTGProject()
            p.audio_markers=[{"path":"tone.wav","start":0,"duration":.5,"volume":.4}]
            for changes in (
                {"fade_in":-.1}, {"fade_in":float("nan")},
                {"fade_out":float("inf")},{"fade_in":.3,"fade_out":.3},
            ):
                p.audio_markers[0].update(changes)
                with self.assertRaisesRegex(ValueError,"fades"):
                    MotionExporter(RenderContext(root))._audio_inputs(p)
                p.audio_markers[0]={"path":"tone.wav","start":0,
                                    "duration":.5,"volume":.4}

    def test_actual_ffmpeg_pcm_amplitude_envelope_when_runtime_available(self):
        """Read *rendered* PCM, not only FFmpeg filter-string documentation."""
        from ttg_ffmpeg_manager import FFmpegManager
        import subprocess
        from math import sqrt
        binary=FFmpegManager().status().path
        if not binary:
            self.skipTest("No installed FFmpeg for direct audio PCM proving on this host")
        with TemporaryDirectory() as t:
            root=Path(t)
            input=root/"tone.wav"
            real_wave(input)
            p=TTGProject(name="real fade",project_type="motion")
            p.canvas=CanvasSpec(width=32,height=24,duration=1.5,fps=25)
            p.audio_markers=[{"path":"tone.wav","start":0,"duration":1.,
                              "volume":1.,"fade_in":.2,"fade_out":.2}]
            audio_args,filters,label=MotionExporter(RenderContext(root))._audio_inputs(p)
            target=root/"rendered.wav"
            cmd=[binary,"-hide_banner","-loglevel","error","-y",
                 "-f","lavfi","-i","anullsrc=r=8000:cl=mono",
                 *audio_args,"-filter_complex",";".join(filters),
                 "-map",label,"-t","1.0","-ar","8000","-ac","1",
                 "-c:a","pcm_s16le",str(target)]
            subprocess.run(cmd,check=True,capture_output=True,timeout=30)
            with wave.open(str(target),"rb") as output:
                self.assertEqual(output.getframerate(),8000)
                self.assertEqual(output.getnchannels(),1)
                buf=output.readframes(output.getnframes())
            values=struct.unpack("<"+"h"*(len(buf)//2),buf)
            def rms(region):
                return sqrt(sum(v*v for v in region)/len(region))
            begin=rms(values[0:600])
            center=rms(values[3500:4500])
            end=rms(values[7400:7900])
            self.assertGreater(center,500)
            self.assertLess(begin,center*.5)
            self.assertLess(end,center*.5)

    def test_existing_studio_tools_dialog_edits_real_audio_fades(self):
        import importlib.util
        if importlib.util.find_spec("PyQt6") is None:
            self.skipTest("Qt not installed on this host; qualified in Windows GUI run")
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt6.QtWidgets import QApplication, QDialog, QDoubleSpinBox, QToolButton
        from PyQt6.QtCore import QTimer
        from ttg_creative_workspace import CreativeWorkspace
        app = QApplication.instance() or QApplication([])
        with TemporaryDirectory() as t:
            root = Path(t)
            real_wave(root/"tone.wav")
            p = TTGProject(name="Editable audio fades",project_type="motion")
            p.canvas = CanvasSpec(width=32,height=24,duration=3,fps=25)
            p.audio_markers=[{"path":"tone.wav","start":0.1,
                              "duration":1.,"volume":.8}]
            project_path = root/"gui.ttgstudio.json"
            p.save(project_path)
            workspace = CreativeWorkspace(project_root=root)
            workspace.project = p
            workspace.project_path = project_path
            menus = [
                item.text() for button in workspace.findChildren(QToolButton)
                if button.menu() for item in button.menu().actions()
            ]
            self.assertIn("Edit Audio Fades",menus)
            workspace.autosave_snapshot = lambda: None
            def approve() -> None:
                dialogs = [q for q in QApplication.topLevelWidgets()
                           if isinstance(q,QDialog)
                           and q.windowTitle()=="Edit Audio Envelope"]
                self.assertEqual(len(dialogs),1)
                controls = dialogs[0].findChildren(QDoubleSpinBox)
                self.assertEqual(len(controls),2)
                controls[0].setValue(.2)
                controls[1].setValue(.3)
                dialogs[0].accept()
            QTimer.singleShot(0, approve)
            workspace.edit_audio_fades()
            self.assertEqual(p.audio_markers[0]["fade_in"],.2)
            self.assertEqual(p.audio_markers[0]["fade_out"],.3)
            _,filters,_=MotionExporter(RenderContext(root))._audio_inputs(p)
            self.assertIn("afade=t=in:st=0:d=0.200",filters[0])
            self.assertIn("afade=t=out:st=0.700:d=0.300",filters[0])
            workspace.close()
            app.processEvents()

    def test_fade_metadata_survives_real_otio_source_roundtrip(self):
        with TemporaryDirectory() as t:
            root=Path(t)
            real_wave(root/"tone.wav")
            p=TTGProject(name="OTIO SoundCraft",project_type="motion")
            p.canvas=CanvasSpec(width=32,height=24,duration=3,fps=30)
            p.audio_markers=[{"path":"tone.wav","start":.4,"duration":1.,
                              "source_in":0,"volume":.6,"fade_in":.1,"fade_out":.25}]
            export_otio(p,root/"audio.otio",project_root=root)
            import_otio(root/"audio.otio",root/"recovered.ttgstudio.json")
            q=TTGProject.load(root/"recovered.ttgstudio.json")
            self.assertEqual(q.audio_markers[0]["fade_in"],.1)
            self.assertEqual(q.audio_markers[0]["fade_out"],.25)
            _,filters,_=MotionExporter(RenderContext(root))._audio_inputs(q)
            self.assertIn("afade=t=out:st=0.750:d=0.250",filters[0])


if __name__=="__main__":
    unittest.main()
