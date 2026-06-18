#!/usr/bin/env python3
"""Build a contact sheet from reference motion proof frames."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FRAMES = ROOT / "outputs" / "reference_motion_frames"
OUT = ROOT / "outputs" / "reference_motion_contact_sheet.jpg"


def main() -> int:
    frames = sorted(FRAMES.glob("reference_frame_*.jpg"))
    if not frames:
        print(f"ERROR: no frames found in {FRAMES}")
        return 1
    sample_count = min(12, len(frames))
    indices = [round(i * (len(frames) - 1) / max(1, sample_count - 1)) for i in range(sample_count)]
    samples = [Image.open(frames[i]).convert("RGB").resize((320, 180), Image.Resampling.LANCZOS) for i in indices]
    sheet = Image.new("RGB", (4 * 320, 3 * 210), (3, 4, 14))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    for n, img in enumerate(samples):
        row, col = divmod(n, 4)
        x, y = col * 320, row * 210
        sheet.paste(img, (x, y))
        draw.text((x + 10, y + 184), f"frame {indices[n]:04d}", fill=(230, 245, 255), font=font)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT, quality=94)
    print(f"Saved contact sheet: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
