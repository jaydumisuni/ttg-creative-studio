#!/usr/bin/env python3
"""Build a video proof from approved visual proof frames.

This is intentionally gated. It will not run unless outputs/ttg_visual_review.json
opens the video proof gate. Release packaging remains blocked.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
FRAMES = OUT / "reference_motion_frames"
VIDEO = OUT / "ttg_reference_video_proof.mp4"


def main() -> int:
    from check_video_gate import main as check_gate

    if check_gate() != 0:
        return 1
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("VIDEO BLOCKED: ffmpeg is not installed or not on PATH.")
        print("Install the Video Export Pack or system FFmpeg before building MP4 proof.")
        return 1
    first_frame = FRAMES / "reference_frame_0000.jpg"
    if not first_frame.exists():
        print("VIDEO BLOCKED: motion frames are missing. Run generate_visual_proof_package.py first.")
        return 1
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        "30",
        "-i",
        str(FRAMES / "reference_frame_%04d.jpg"),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(VIDEO),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Video proof written: {VIDEO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
