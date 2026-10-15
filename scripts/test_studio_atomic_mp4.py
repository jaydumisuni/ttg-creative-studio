#!/usr/bin/env python3
"""G4 export crash-safety: preserve prior MP4 on errors and publish atomically."""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from ttg_action_engine import ActionEngine
from ttg_canvas_engine import RenderContext
from ttg_motion_exporter import MotionExporter

checks=[]

def check(test, predicate):
    if not predicate: raise AssertionError(test)
    checks.append(test)


def main():
    with tempfile.TemporaryDirectory(prefix="ttg-atomic-mp4-") as temp:
        root=Path(temp)
        project=ActionEngine().new_project("Atomic export","motion")
        project.canvas.width=64
        project.canvas.height=64
        project.canvas.fps=4
        project.canvas.duration=.5
        ActionEngine().add_shape(project,"rectangle",0,0)
        exporter=MotionExporter(RenderContext(root))
        output=root/"final.mp4"
        original=b"previous approved video version"
        output.write_bytes(original)
        first=True

        def fail_subprocess(argv,*args,**kwargs):
            target=Path(argv[-1])
            check("encoder writes into temporary MP4",target != output and
                  target.suffix==".mp4" and target.parent==root)
            target.write_bytes(b"incomplete video")
            raise subprocess.CalledProcessError(1,argv)

        with patch("ttg_motion_exporter.FFmpegManager.require", return_value="ffmpeg"), \
             patch("ttg_motion_exporter.subprocess.run",side_effect=fail_subprocess):
            try:exporter.export_mp4(project,output,root/"frame-work")
            except subprocess.CalledProcessError:checks.append("encoder failure propagates")
            else:raise AssertionError("Encoder failure was hidden")
        check("failed export preserves prior MP4", output.read_bytes()==original)
        check("failed encoder cleans partial MP4",list(root.glob(".final-*.mp4"))==[])

        def no_bytes(argv,*args,**kwargs):
            return subprocess.CompletedProcess(argv,0)
        with patch("ttg_motion_exporter.FFmpegManager.require", return_value="ffmpeg"), \
             patch("ttg_motion_exporter.subprocess.run",side_effect=no_bytes):
            try:exporter.export_mp4(project,output,root/"frame-work")
            except RuntimeError as exc:
                check("zero-byte encode is rejected","without producing" in str(exc))
            else:raise AssertionError("Empty encode published")
        check("empty encode preserves prior export",output.read_bytes()==original)
        check("empty encode cleans staged file",list(root.glob(".final-*.mp4"))==[])

        def mock_encode(argv,*args,**kwargs):
            Path(argv[-1]).write_bytes(b"valid-test-encoded-video")
            return subprocess.CompletedProcess(argv,0)
        with patch("ttg_motion_exporter.FFmpegManager.require", return_value="ffmpeg"), \
             patch("ttg_motion_exporter.subprocess.run",side_effect=mock_encode), \
             patch("ttg_motion_exporter.os.replace",side_effect=OSError(28,"No space left on device")):
            try:exporter.export_mp4(project,output,root/"frame-work")
            except OSError:checks.append("out-of-space publication failure propagates")
            else:raise AssertionError("Rename failure was hidden")
        check("disk failure preserves older MP4",output.read_bytes()==original)
        check("disk failure cleans temporary export",list(root.glob(".final-*.mp4"))==[])

        with patch("ttg_motion_exporter.FFmpegManager.require", return_value="ffmpeg"), \
             patch("ttg_motion_exporter.subprocess.run",side_effect=mock_encode):
            actual=exporter.export_mp4(project,output,root/"frame-work")
        check("successful MP4 atomically publishes",actual==output and
              output.read_bytes()==b"valid-test-encoded-video")
        check("successful encode has no residual tmp",not list(root.glob(".final-*.mp4")))
        check("all frame scratch removed",not list((root/"frame-work").glob("ttg-render-*")))
    print(json.dumps({"result":"PASS","checks_count":len(checks),"checks":checks},indent=2))


if __name__=="__main__":
    main()
