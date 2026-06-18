#!/usr/bin/env python3
"""Verify still first, then render and score repo-native motion proof frames."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_reference_still_renderer import render_reference_still
from ttg_reference_motion_renderer import render_reference_motion_frames
from score_reference_still import score_image


def main() -> int:
    still = ROOT / "outputs" / "ttg_reference_still.jpg"
    render_reference_still(ROOT, still)
    score = score_image(still)
    if not score["passed"]:
        print("Still verification failed; motion render blocked.")
        print(score)
        return 1

    frames_dir = ROOT / "outputs" / "reference_motion_frames"
    frames = render_reference_motion_frames(ROOT, frames_dir, frames=48)
    if len(frames) != 48:
        print(f"ERROR: expected 48 frames, got {len(frames)}")
        return 1
    if not all(path.exists() and path.stat().st_size > 0 for path in frames):
        print("ERROR: one or more rendered frames are missing/empty")
        return 1

    from build_motion_contact_sheet import main as build_sheet
    from score_reference_motion import main as score_motion
    from build_motion_gif_preview import main as build_gif

    sheet_code = build_sheet()
    if sheet_code != 0:
        return sheet_code
    motion_code = score_motion()
    if motion_code != 0:
        return motion_code
    gif_code = build_gif()
    if gif_code != 0:
        return gif_code

    print(f"Motion proof frames rendered, scored, contact-sheeted and GIF-previewed: {len(frames)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
