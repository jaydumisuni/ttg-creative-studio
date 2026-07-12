#!/usr/bin/env python3
"""Self-test Creative Studio ad workflow from generated folder and ZIP assets.

This proves the engine/workflow can create an editable ad project and a visually
meaningful composed contact sheet before final UI polish.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from build_ad_project_from_assets import build_ad_project
from render_ad_project_contact_sheet import render_contact_sheet
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


def gradient_background(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size)
    pixels = image.load()
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(round(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        for x in range(width):
            pixels[x, y] = color
    return image


def add_glow(base: Image.Image, box: tuple[int, int, int, int], color: tuple[int, int, int], blur: int = 38) -> None:
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    draw.ellipse(box, fill=(*color, 175))
    glow = glow.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(glow)


def draw_microphone(draw: ImageDraw.ImageDraw, center: tuple[int, int], color: tuple[int, int, int]) -> None:
    x, y = center
    draw.rounded_rectangle((x - 54, y - 150, x + 54, y + 10), radius=54, outline=color, width=14)
    draw.arc((x - 100, y - 80, x + 100, y + 120), start=0, end=180, fill=color, width=14)
    draw.line((x, y + 105, x, y + 190), fill=color, width=14)
    draw.line((x - 75, y + 190, x + 75, y + 190), fill=color, width=14)


def draw_network(draw: ImageDraw.ImageDraw, center: tuple[int, int], color: tuple[int, int, int]) -> None:
    x, y = center
    nodes = [(x, y - 150), (x - 150, y - 20), (x + 150, y - 20), (x - 90, y + 150), (x + 90, y + 150)]
    for a, b in [(0, 1), (0, 2), (1, 3), (2, 4), (3, 4), (1, 2)]:
        draw.line((*nodes[a], *nodes[b]), fill=color, width=10)
    for nx, ny in nodes:
        draw.ellipse((nx - 28, ny - 28, nx + 28, ny + 28), fill=(5, 8, 24), outline=color, width=10)


def draw_rings(draw: ImageDraw.ImageDraw, center: tuple[int, int], color: tuple[int, int, int]) -> None:
    x, y = center
    draw.ellipse((x - 150, y - 110, x + 20, y + 60), outline=color, width=18)
    draw.ellipse((x - 20, y - 60, x + 150, y + 110), outline=(255, 255, 255), width=18)
    draw.polygon([(x - 95, y - 105), (x - 65, y - 150), (x - 35, y - 105)], fill=(255, 255, 255), outline=color)


def draw_rocket(draw: ImageDraw.ImageDraw, center: tuple[int, int], color: tuple[int, int, int]) -> None:
    x, y = center
    draw.ellipse((x - 62, y - 190, x + 62, y + 80), fill=(14, 19, 50), outline=color, width=14)
    draw.polygon([(x - 62, y + 30), (x - 145, y + 130), (x - 52, y + 100)], fill=color)
    draw.polygon([(x + 62, y + 30), (x + 145, y + 130), (x + 52, y + 100)], fill=(188, 19, 254))
    draw.ellipse((x - 26, y - 90, x + 26, y - 38), fill=(0, 229, 255), outline=(255, 255, 255), width=5)
    draw.polygon([(x - 40, y + 75), (x, y + 210), (x + 40, y + 75)], fill=(255, 120, 40), outline=(255, 245, 180))


def make_scene(index: int) -> Image.Image:
    themes = [
        ("LIVE CONCERT", "Music • Tickets • VIP Access", (11, 8, 36), (66, 10, 92), (255, 45, 210)),
        ("TECH SUMMIT", "Speakers • Networking • QR Entry", (4, 17, 42), (0, 70, 92), (0, 229, 255)),
        ("WEDDING NIGHT", "Invites • Guests • Memories", (35, 7, 39), (102, 24, 74), (255, 165, 225)),
        ("PRODUCT LAUNCH", "Reveal • Stream • Share", (8, 10, 42), (35, 14, 94), (126, 100, 255)),
    ]
    title, subtitle, top, bottom, accent = themes[index % len(themes)]
    image = gradient_background((900, 1280), top, bottom).convert("RGBA")
    add_glow(image, (100, 170, 800, 870), accent, blur=75)
    add_glow(image, (260, 310, 640, 760), (0, 229, 255), blur=42)
    draw = ImageDraw.Draw(image)
    title_font = load_font(72, bold=True)
    sub_font = load_font(34)
    small_font = load_font(25, bold=True)

    draw.rounded_rectangle((72, 72, 828, 1180), radius=62, fill=(3, 6, 22, 120), outline=accent, width=8)
    draw.rounded_rectangle((105, 110, 795, 235), radius=30, fill=(5, 8, 28, 205), outline=(0, 229, 255), width=5)
    draw.text((135, 143), "THETECHGUY DIGITAL EVENTS", font=small_font, fill=(255, 255, 255))

    center = (450, 570)
    if index % 4 == 0:
        draw_microphone(draw, center, accent)
    elif index % 4 == 1:
        draw_network(draw, center, accent)
    elif index % 4 == 2:
        draw_rings(draw, center, accent)
    else:
        draw_rocket(draw, center, accent)

    box = draw.textbbox((0, 0), title, font=title_font)
    text_width = box[2] - box[0]
    draw.text(((900 - text_width) / 2, 850), title, font=title_font, fill=(255, 255, 255), stroke_width=3, stroke_fill=accent)
    sub_box = draw.textbbox((0, 0), subtitle, font=sub_font)
    sub_width = sub_box[2] - sub_box[0]
    draw.text(((900 - sub_width) / 2, 960), subtitle, font=sub_font, fill=(0, 229, 255))
    draw.rounded_rectangle((190, 1045, 710, 1125), radius=26, fill=accent)
    cta = "CREATE • INVITE • CELEBRATE"
    cta_box = draw.textbbox((0, 0), cta, font=small_font)
    draw.text(((900 - (cta_box[2] - cta_box[0])) / 2, 1070), cta, font=small_font, fill=(3, 5, 18))
    return image.convert("RGB")


def make_sample_assets(asset_dir: Path, count: int = 4) -> None:
    if asset_dir.exists():
        shutil.rmtree(asset_dir)
    asset_dir.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        make_scene(index).save(asset_dir / f"scene_{index + 1:02d}.jpg", quality=94)


def make_zip(asset_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(asset_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(asset_dir))


def publish_artifacts(project_path: Path, contact_sheet: Path, zip_project_path: Path) -> None:
    artifact_dir = Path(os.environ.get("TTG_AD_WORKFLOW_ARTIFACT_DIR", ROOT / "outputs" / "ad_workflow"))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(project_path, artifact_dir / project_path.name)
    shutil.copy2(zip_project_path, artifact_dir / zip_project_path.name)
    shutil.copy2(contact_sheet, artifact_dir / contact_sheet.name)
    report = artifact_dir / "AD_WORKFLOW_PROOF.md"
    report.write_text(
        "# TTG Ad Workflow Proof\n\n"
        "This artifact proves the engine/workflow path with composed, visually meaningful benchmark scenes.\n\n"
        f"- Folder project: `{project_path.name}`\n"
        f"- ZIP project: `{zip_project_path.name}`\n"
        f"- Contact sheet: `{contact_sheet.name}`\n\n"
        "Pipeline: folder/ZIP assets → editable `.ttgstudio.json` project → composed visual contact sheet proof.\n",
        encoding="utf-8",
    )


def validate_project(project_path: Path, expected_assets: int = 4) -> tuple[TTGProject, list[bool]]:
    loaded = TTGProject.load(project_path)
    image_layers = [layer for layer in loaded.layers if layer.type == "image"]
    checks = [
        project_path.exists(),
        loaded.project_type == "motion",
        loaded.canvas.width == 1080,
        loaded.canvas.height == 1920,
        loaded.canvas.fps == 30,
        loaded.export.get("workflow") == "ad_from_assets",
        loaded.export.get("creative_studio_test", {}).get("normalized_images") == expected_assets,
        len(loaded.assets) == expected_assets,
        len(image_layers) == expected_assets,
        all(layer.keyframes for layer in image_layers),
        any(layer.name == "Ad Title" for layer in loaded.layers),
        any(layer.name == "Call To Action" for layer in loaded.layers),
        len(loaded.audio_markers) >= 2,
    ]
    return loaded, checks


def main() -> int:
    work = Path(tempfile.gettempdir()) / "ttg_ad_project_workflow_self_test"
    asset_dir = work / "assets"
    zip_path = work / "ad_assets.zip"
    folder_output = work / "ttg_ad_from_folder.ttgstudio.json"
    zip_output = work / "ttg_ad_from_zip.ttgstudio.json"
    contact_sheet = work / "ttg_ad_contact_sheet.jpg"
    make_sample_assets(asset_dir)
    make_zip(asset_dir, zip_path)

    folder_project = build_ad_project(asset_dir, folder_output, "Workflow Folder Self Test Ad")
    zip_project = build_ad_project(zip_path, zip_output, "Workflow ZIP Self Test Ad", workspace=work / "zip_import_workspace")
    rendered = render_contact_sheet(zip_output, contact_sheet)
    loaded_folder, folder_checks = validate_project(folder_output)
    loaded_zip, zip_checks = validate_project(zip_output)
    publish_artifacts(folder_output, rendered, zip_output)

    with Image.open(rendered) as proof:
        proof_size = proof.size
    checks = [
        rendered.exists(),
        proof_size[0] >= 800,
        proof_size[1] >= 600,
        folder_project.canvas.duration == loaded_folder.canvas.duration,
        zip_project.canvas.duration == loaded_zip.canvas.duration,
        *folder_checks,
        *zip_checks,
    ]
    if not all(checks):
        print("Ad project workflow self-test failed")
        print(checks)
        print(f"Folder project: {folder_output}")
        print(f"ZIP project: {zip_output}")
        print(f"Contact sheet: {rendered}")
        return 1
    print("Ad project workflow self-test passed")
    print(f"Folder project: {folder_output}")
    print(f"ZIP project: {zip_output}")
    print(f"Contact sheet: {rendered} {proof_size}")
    print(f"Folder assets: {len(loaded_folder.assets)} ZIP assets: {len(loaded_zip.assets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
