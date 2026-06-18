#!/usr/bin/env python3
"""Score reference motion proof frames for visible change and non-empty output."""

from __future__ import annotations

import json
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "outputs" / "reference_motion_frames"
REPORT = ROOT / "outputs" / "reference_motion_score.json"


def main() -> int:
    frames = sorted(FRAMES.glob("reference_frame_*.jpg"))
    if len(frames) < 12:
        print(f"ERROR: expected at least 12 frames, got {len(frames)}")
        return 1
    first = Image.open(frames[0]).convert("RGB").resize((320, 180))
    middle = Image.open(frames[len(frames)//2]).convert("RGB").resize((320, 180))
    last = Image.open(frames[-1]).convert("RGB").resize((320, 180))
    diff_first_last = ImageStat.Stat(ImageChops.difference(first, last)).mean
    diff_mid_last = ImageStat.Stat(ImageChops.difference(middle, last)).mean
    motion_score = sum(diff_first_last) / 3
    settle_score = sum(diff_mid_last) / 3
    last_stat = ImageStat.Stat(last)
    contrast = sum(last_stat.stddev) / 3
    result = {
        "frame_count": len(frames),
        "motion_score": motion_score,
        "settle_score": settle_score,
        "final_contrast": contrast,
        "checks": {
            "enough_frames": len(frames) >= 48,
            "motion_visible": motion_score >= 12,
            "final_not_flat": contrast >= 30,
        },
    }
    result["passed"] = all(result["checks"].values())
    REPORT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
