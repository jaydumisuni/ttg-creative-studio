#!/usr/bin/env python3
"""Build a lightweight GIF preview from reference motion proof frames."""

from __future__ import annotations

from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "outputs" / "reference_motion_frames"
OUT = ROOT / "outputs" / "reference_motion_preview.gif"


def main() -> int:
    frames = sorted(FRAMES.glob("reference_frame_*.jpg"))
    if len(frames) < 12:
        print(f"ERROR: expected at least 12 frames, got {len(frames)}")
        return 1
    # Use every second frame to keep artifact small while still showing motion.
    selected = frames[::2]
    images = [Image.open(path).convert("P", palette=Image.Palette.ADAPTIVE).resize((640, 360), Image.Resampling.LANCZOS) for path in selected]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(
        OUT,
        save_all=True,
        append_images=images[1:],
        duration=70,
        loop=0,
        optimize=True,
    )
    print(f"Saved GIF preview: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
