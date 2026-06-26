#!/usr/bin/env python3
"""Render a simple contact sheet proof from a TTG ad project.

This is not the final video renderer. It is an engine/workflow proof that the
ad-project JSON can produce visual scene output before UI polish.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PIL import Image, ImageDraw, ImageFont

from ttg_project_schema import TTGProject


def fit_image(image: Image.Image, box: tuple[int, int]) -> Image.Image:
    target_w, target_h = box
    copy = image.convert("RGB")
    copy.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (target_w, target_h), (5, 6, 20))
    x = (target_w - copy.width) // 2
    y = (target_h - copy.height) // 2
    canvas.paste(copy, (x, y))
    return canvas


def render_contact_sheet(project_path: Path, output: Path, max_scenes: int = 6) -> Path:
    project = TTGProject.load(project_path)
    image_layers = [layer for layer in project.layers if layer.type == "image"][:max_scenes]
    if not image_layers:
        raise SystemExit("No image scene layers found")

    thumb_w, thumb_h = 260, 460
    gap = 24
    cols = min(3, len(image_layers))
    rows = (len(image_layers) + cols - 1) // cols
    sheet_w = cols * thumb_w + (cols + 1) * gap
    sheet_h = 120 + rows * (thumb_h + 70) + gap
    sheet = Image.new("RGB", (sheet_w, sheet_h), (3, 5, 18))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    draw.text((gap, 24), project.name, fill=(255, 255, 255), font=font)
    draw.text((gap, 52), f"{project.canvas.width}x{project.canvas.height} • {project.canvas.duration:.2f}s • {len(image_layers)} scenes", fill=(0, 229, 255), font=font)

    for index, layer in enumerate(image_layers):
        row = index // cols
        col = index % cols
        x = gap + col * (thumb_w + gap)
        y = 100 + row * (thumb_h + 70)
        path = Path(str(layer.properties.get("path", "")))
        if path.exists():
            thumb = fit_image(Image.open(path), (thumb_w, thumb_h))
        else:
            thumb = Image.new("RGB", (thumb_w, thumb_h), (25, 20, 45))
            ImageDraw.Draw(thumb).text((20, 220), "Missing asset", fill=(255, 80, 120), font=font)
        sheet.paste(thumb, (x, y))
        draw.rectangle((x, y, x + thumb_w, y + thumb_h), outline=(0, 229, 255), width=2)
        draw.text((x, y + thumb_h + 10), f"Scene {index + 1}: {layer.properties.get('motion', 'static')}", fill=(255, 255, 255), font=font)
        draw.text((x, y + thumb_h + 30), f"{layer.properties.get('start_time')}s → {layer.properties.get('end_time')}s", fill=(188, 19, 254), font=font)

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=92)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "ttg_ad_contact_sheet.jpg")
    args = parser.parse_args()
    output = render_contact_sheet(args.project, args.output)
    print(f"Saved ad contact sheet: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
