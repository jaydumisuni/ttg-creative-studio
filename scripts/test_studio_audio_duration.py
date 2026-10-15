#!/usr/bin/env python3
"""Decode real H.264/AAC outputs and verify an audio clip never ends video early.

Cross-platform CI uses an isolated test-only FFmpeg binary. No fake encoder.
"""
from __future__ import annotations

import json
import math
import re
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import imageio_ffmpeg
from ttg_action_engine import ActionEngine
from ttg_canvas_engine import RenderContext
from ttg_motion_exporter import MotionExporter


def probe_duration(executable: str, video: Path) -> tuple[float, bool, bool]:
    result = subprocess.run(
        [executable, "-hide_banner", "-i", str(video)],
        capture_output=True, text=True, timeout=15,
    )
    info = result.stderr
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", info)
    if match is None:
        raise AssertionError("FFmpeg could not decode output's container duration: " + info[-650:])
    duration = int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3])
    return duration, "Video: h264" in info, "Audio: aac" in info


def main() -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    checks: list[str] = []
    with tempfile.TemporaryDirectory(prefix="ttg-audio-duration-") as temp:
        root = Path(temp)
        project = ActionEngine().new_project("Authoritative two-second timeline", "motion")
        project.canvas.width = project.canvas.height = 64
        project.canvas.duration = 2.0
        project.canvas.fps = 10
        ActionEngine().add_shape(project, "rectangle", 0, 0)

        for label, length in (("short-audio", .25), ("long-audio", 3.5)):
            source = root / (label + ".wav")
            with wave.open(str(source), "wb") as wave_file:
                wave_file.setnchannels(1)
                wave_file.setsampwidth(2)
                wave_file.setframerate(8000)
                samples = [
                    struct.pack("<h", int(1000 * math.sin(index / 11)))
                    for index in range(round(length * 8000))
                ]
                wave_file.writeframes(b"".join(samples))

            project.audio_markers = [{"path": source.name, "start": 0, "volume": .8}]
            final = root / (label + ".mp4")
            with patch("ttg_motion_exporter.FFmpegManager.require", return_value=ffmpeg):
                result = MotionExporter(RenderContext(root)).export_mp4(
                    project, final, root / "render-work"
                )
            if result != final or not final.is_file() or final.stat().st_size < 1000:
                raise AssertionError(label + ": real FFmpeg did not publish the MP4")
            duration, video, audio = probe_duration(ffmpeg, final)
            if not 1.9 <= duration <= 2.1:
                raise AssertionError(
                    f"{label}: expected a two-second animation, decoded {duration}s"
                )
            if not video or not audio:
                raise AssertionError(f"{label}: expected real H.264 video and AAC audio")
            if list(root.glob(f".{final.stem}-*.mp4")):
                raise AssertionError("Atomic temporary output not cleaned")
            if list((root / "render-work").glob("ttg-render-*")):
                raise AssertionError("Scratch render frames not cleaned")
            checks.append(label + " preserves the full video with actual H.264/AAC")
        print(json.dumps({"result": "PASS", "checks": len(checks), "details": checks}, indent=2))


if __name__ == "__main__":
    main()
