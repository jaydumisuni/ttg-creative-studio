#!/usr/bin/env python3
"""Render composed scene previews from a TTG ad project.

The contact sheet is a visual workflow proof: imported assets are combined with
project title/CTA layers, motion labels and branded overlays rather than shown as
raw thumbnails only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from ttg_project_schema import TTGProject


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def cover_image(image: Image.Image, box: tuple[int, int]) -> Image.Image:
    target_w, target_h = box
    source = image.convert("RGB")
    scale = max(target_w / source.width, target_h / source.height)
    resized = source.resize((max(1, round(source.width * scale)), max(1, round(source.height * scale))), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - target_w) // 2)
    top = max(0, (resized.height - target_h) // 2)
    return resized.crop((left, top, left + target_w, top + target_h))


def project_text(project: TTGProject, layer_name: str, fallback: str) -> str:
    for layer in project.layers:
        if layer.name == layer_name:
            return str(layer.properties.get("text", fallback))
    return fallback


def gradient_overlay(size: tuple[int, int], top_alpha: int, bottom_alpha: int) -> Image.Image:
    width, height = size
    overlay = Image.new("RGBA", size, (0, 0, 0, 0))
    pixels = overlay.load()
    for y in range(height):
        ratio = y / max(1, height - 1)
        alpha = round(top_alpha + (bottom_alpha - top_alpha) * ratio)
        for x in range(width):
            pixels[x, y] = (3, 5, 20, alpha)
    return overlay


def render_scene(project: TTGProject, layer, index: int, size: tuple[int, int]) -> Image.Image:
    width, height = size
    path = Path(str(layer.properties.get("path", "")))
    if path.exists():
        scene = cover_image(Image.open(path), size)
        scene = ImageEnhance.Contrast(scene).enhance(1.12)
        scene = ImageEnhance.Color(scene).enhance(1.15)
    else:
        scene = Image.new("RGB", size, (20, 12, 45))

    base = scene.convert("RGBA")
    base.alpha_composite(gradient_overlay(size, 40, 205))
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.rounded_rectangle((12, 12, width - 13, height - 13), radius=22, outline=(0, 229, 255, 180), width=4)
    blurred = glow.filter(ImageFilter.GaussianBlur(8))
    base.alpha_composite(blurred)
    base.alpha_composite(glow)

    draw = ImageDraw.Draw(base)
    title_font = load_font(18, bold=True)
    cta_font = load_font(11, bold=True)
    small_font = load_font(9)
    badge_font = load_font(9, bold=True)
    title = project_text(project, "Ad Title", "THETECHGUY DIGITAL EVENTS")
    cta = project_text(project, "Call To Action", "Create invites • Manage guests • Share events")

    draw.rounded_rectangle((22, 26, width - 22, 72), radius=12, fill=(5, 6, 20, 185), outline=(188, 19, 254, 220), width=2)
    title_box = draw.textbbox((0, 0), title, font=title_font)
    title_width = title_box[2] - title_box[0]
    title_scale = min(1.0, (width - 56) / max(1, title_width))
    if title_scale < 1.0:
        title_font = load_font(max(11, round(18 * title_scale)), bold=True)
        title_box = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_box[2] - title_box[0]
    draw.text(((width - title_width) / 2, 39), title, font=title_font, fill=(247, 250, 255), stroke_width=1, stroke_fill=(188, 19, 254))

    motion = str(layer.properties.get("motion", "static")).replace("_", " ").upper()
    badge = f"SCENE {index + 1}  •  {motion}"
    badge_box = draw.textbbox((0, 0), badge, font=badge_font)
    badge_width = badge_box[2] - badge_box[0]
    draw.rounded_rectangle((22, 84, 36 + badge_width, 108), radius=8, fill=(0, 229, 255, 210))
    draw.text((29, 90), badge, font=badge_font, fill=(3, 5, 18))

    footer_top = height - 112
    draw.rounded_rectangle((20, footer_top, width - 20, height - 24), radius=18, fill=(4, 5, 18, 220), outline=(0, 229, 255, 190), width=2)
    draw.text((34, footer_top + 18), cta, font=cta_font, fill=(247, 250, 255))
    start = layer.properties.get("start_time", 0)
    end = layer.properties.get("end_time", 0)
    draw.text((34, footer_top + 48), f"{start}s → {end}s", font=small_font, fill=(0, 229, 255))
    draw.text((34, footer_top + 68), "thetechguyds.com", font=small_font, fill=(188, 19, 254))
    return base.convert("RGB")


def render_contact_sheet(project_path: Path, output: Path, max_scenes: int = 6) -> Path:
    project = TTGProject.load(project_path)
    image_layers = [layer for layer in project.layers if layer.type == "image"][:max_scenes]
    if not image_layers:
        raise SystemExit("No image scene layers found")

    thumb_w, thumb_h = 300, 520
    gap = 26
    cols = min(3, len(image_layers))
    rows = (len(image_layers) + cols - 1) // cols
    sheet_w = cols * thumb_w + (cols + 1) * gap
    sheet_h = 118 + rows * (thumb_h + 58) + gap
    sheet = Image.new("RGB", (sheet_w, sheet_h), (3, 5, 18))
    draw = ImageDraw.Draw(sheet)
    title_font = load_font(20, bold=True)
    meta_font = load_font(12)
    draw.text((gap, 22), project.name, fill=(255, 255, 255), font=title_font)
    draw.text((gap, 58), f"{project.canvas.width}×{project.canvas.height}  •  {project.canvas.duration:.2f}s  •  {len(image_layers)} editable scenes", fill=(0, 229, 255), font=meta_font)

    for index, layer in enumerate(image_layers):
        row = index // cols
        col = index % cols
        x = gap + col * (thumb_w + gap)
        y = 100 + row * (thumb_h + 58)
        scene = render_scene(project, layer, index, (thumb_w, thumb_h))
        sheet.paste(scene, (x, y))
        draw.text((x, y + thumb_h + 14), f"Layer: {layer.name}", fill=(255, 255, 255), font=meta_font)

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=94)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "outputs" / "ttg_ad_contact_sheet.jpg")
    args = parser.parse_args()
    output = render_contact_sheet(args.project, args.output)
    print(f"Saved composed ad contact sheet: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
