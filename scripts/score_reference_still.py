#!/usr/bin/env python3
"""Score the repo-native THETECHGUY reference still for visual richness.

This is not an artistic judge. It is a guardrail so the renderer cannot pass with
a flat, empty or low-detail frame. Human approval is still required before video.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IMAGE = ROOT / "outputs" / "ttg_reference_still.jpg"
DEFAULT_REPORT = ROOT / "outputs" / "ttg_reference_still_score.json"


def score_image(path: Path) -> dict:
    img = Image.open(path).convert("RGB")
    width, height = img.size
    stat = ImageStat.Stat(img)
    extrema = img.getextrema()
    brightness = sum(stat.mean) / 3
    contrast = sum(stat.stddev) / 3

    pixels = img.resize((320, 180)).getdata()
    neon_pixels = 0
    dark_pixels = 0
    for r, g, b in pixels:
        if max(r, g, b) < 28:
            dark_pixels += 1
        if (b > 120 and g > 70) or (r > 120 and b > 120):
            neon_pixels += 1
    total = 320 * 180
    neon_ratio = neon_pixels / total
    dark_ratio = dark_pixels / total

    # Edge/detail proxy using grayscale neighbor differences.
    gray = img.convert("L").resize((320, 180))
    data = list(gray.getdata())
    detail_sum = 0
    comparisons = 0
    for y in range(179):
        row = y * 320
        next_row = (y + 1) * 320
        for x in range(319):
            v = data[row + x]
            detail_sum += abs(v - data[row + x + 1])
            detail_sum += abs(v - data[next_row + x])
            comparisons += 2
    detail = detail_sum / max(1, comparisons)

    checks = {
        "resolution_ok": width >= 1920 and height >= 1080,
        "contrast_ok": contrast >= 38,
        "neon_ok": neon_ratio >= 0.045,
        "dark_base_ok": dark_ratio >= 0.20,
        "detail_ok": detail >= 9,
        "not_blank_ok": max(channel[1] for channel in extrema) - min(channel[0] for channel in extrema) >= 160,
    }
    passed = all(checks.values())
    return {
        "path": str(path),
        "width": width,
        "height": height,
        "brightness": brightness,
        "contrast": contrast,
        "neon_ratio": neon_ratio,
        "dark_ratio": dark_ratio,
        "detail_score": detail,
        "checks": checks,
        "passed": passed,
    }


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IMAGE
    report = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_REPORT
    if not path.exists():
        print(f"ERROR: image not found: {path}")
        return 1
    result = score_image(path)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
