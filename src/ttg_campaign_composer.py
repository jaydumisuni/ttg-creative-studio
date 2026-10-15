#!/usr/bin/env python3
"""Offline, editable campaign compositions for TTG Creative Studio.

These are original procedural product illustrations and native editable layers,
not generated images from an AI model.  Every asset stays inside the project.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from ttg_action_engine import ActionEngine
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_export_service import ExportService
from ttg_project_schema import Asset, TTGProject, new_id
from ttg_text_renderer import load_font
from ttg_validation import ProjectValidator

FORMATS = {
    "flagship": ("Flagship · Portrait", 1080, 1350),
    "social": ("Social · Square", 1080, 1080),
    "wide": ("Launch · Widescreen", 1920, 1080),
}
_ACCENTS = {"aqua": "#71F4E6", "violet": "#BE9BFF", "amber": "#FFCC82"}

@dataclass(frozen=True)
class CampaignBrief:
    layout: str = "flagship"
    brand: str = "THETECHGUY"
    headline: str = "BEYOND THE ORDINARY."
    subhead: str = "Designed to make your next move extraordinary."
    product_name: str = "NEXT GENERATION"
    cta: str = "DISCOVER MORE"
    website: str = "thetechguyds.com"
    accent: str = "aqua"
    image_path: str | None = None

    def validate(self) -> None:
        if self.layout not in FORMATS or self.accent not in _ACCENTS:
            raise ValueError("Unknown campaign layout or accent")
        for key, limit in [("brand", 35), ("headline", 85), ("subhead", 125),
                           ("product_name", 45), ("cta", 28), ("website", 65)]:
            value = getattr(self, key)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{key} must contain 1–{limit} characters")
            if any(ord(c) < 32 and not (key == "headline" and c == "\n") for c in value):
                raise ValueError(f"{key} contains a control character")
        if self.image_path is not None and not Path(self.image_path).is_file():
            raise ValueError("Product image file is not available")


def _color(v: str) -> tuple[int, int, int]:
    return tuple(bytes.fromhex(v.lstrip("#")))  # type: ignore[return-value]


def _glow(image: Image.Image, box: tuple[int, int, int, int],
          color: str, blur: int, alpha: int = 110) -> None:
    layer = Image.new("RGBA", image.size)
    d = ImageDraw.Draw(layer)
    d.ellipse(box, fill=(*_color(color), alpha))
    image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def _backdrop(w: int, h: int, accent: str, seed: int = 31) -> Image.Image:
    im = Image.new("RGBA", (w, h), "#070D19")
    draw = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        draw.line((0, y, w, y), fill=(int(7 + 9*t), int(13 + 12*t),
                                       int(27 + 14*t), 255))
    _glow(im, (int(-.27*w), int(.03*h), int(.49*w), int(.72*h)),
          accent, max(36, w//16), 90)
    _glow(im, (int(.48*w), int(.17*h), int(1.31*w), int(.99*h)),
          "#6242C4", max(44, w//13), 110)
    _glow(im, (int(.2*w), int(.54*h), int(.94*w), int(1.21*h)),
          "#167C96", max(36, w//15), 85)
    overlay = Image.new("RGBA", im.size)
    d = ImageDraw.Draw(overlay)
    step = max(66, w // 14)
    for x in range(0, w, step):
        d.line((x, 0, x, h), fill=(150, 206, 251, 13))
    for y in range(0, h, step):
        d.line((0, y, w, y), fill=(150, 206, 251, 11))
    rng = random.Random(seed)
    for _ in range(max(75, w*h//8500)):
        x, y = rng.randrange(w), rng.randrange(h)
        radius = rng.choice([1, 1, 1, 2])
        d.ellipse((x-radius, y-radius, x+radius, y+radius),
                  fill=(211, 241, 255, rng.randrange(24, 110)))
    im.alpha_composite(overlay)
    return im


def _rings(w: int, h: int, accent: str) -> Image.Image:
    im = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im)
    cx, cy = w//2, h//2
    for n in range(4):
        rx = min(w, h)*(.31+n*.08)
        bounds = (int(cx-rx), int(cy-rx), int(cx+rx), int(cy+rx))
        d.arc(bounds, 195, 317, fill=(*_color(accent), max(32, 170-n*26)), width=3)
        d.arc(bounds, 12, 83, fill=(176, 132, 255, max(28, 130-n*23)), width=2)
    for n in range(48):
        theta = n * math.tau/48
        r = min(w, h)*.42
        x, y = cx+math.cos(theta)*r, cy+math.sin(theta)*r
        d.ellipse((x-1, y-1, x+1, y+1), fill=(*_color(accent), 60))
    return im


def _phone(accent: str) -> Image.Image:
    """Original procedural transparent hero asset. No donor/product photo."""
    w, h = 700, 1020
    im = Image.new("RGBA", (w, h))
    shadow = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(shadow)
    d.rounded_rectangle((123, 60, 563, 954), radius=75, fill=(0, 0, 0, 190))
    im.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(44)))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((104, 34, 548, 930), radius=66,
                        fill=(40, 55, 77, 255), outline=(116, 207, 221, 245), width=6)
    d.rounded_rectangle((113, 42, 538, 916), radius=61,
                        fill=(5, 14, 27, 255), outline=(21, 42, 65, 255), width=5)
    screen = Image.new("RGBA", (w, h))
    sd = ImageDraw.Draw(screen)
    for y in range(53, 904):
        t = (y-53)/851
        sd.line((123, y, 529, y), fill=(int(8+18*t), int(26+13*t), int(53+26*t), 255))
    _glow(screen, (-130, 265, 455, 1015), accent, 83, 150)
    _glow(screen, (255, -125, 790, 570), "#8458D5", 88, 175)
    d = ImageDraw.Draw(screen)
    for n in range(34):
        points = []
        for y in range(170, 820, 7):
            t = (y-170)/650
            x = 323 + math.sin(t*3.65+n*.11)*113 - n*2.7
            points.append((int(x), y))
        d.line(points, fill=(*_color(accent), max(14, 182 - n*4)), width=3)
    clip = Image.new("L", (w, h), 0)
    ImageDraw.Draw(clip).rounded_rectangle((124, 54, 527, 903), radius=46, fill=255)
    screen.putalpha(ImageChops_multiply(screen.getchannel("A"), clip))
    im.alpha_composite(screen)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((254, 65, 391, 88), radius=14, fill=(3, 8, 18, 255))
    d.ellipse((394, 72, 409, 87), fill=(32, 77, 108, 255))
    d.rounded_rectangle((96, 245, 105, 337), radius=3, fill=(130, 166, 184, 255))
    d.line((122, 110, 122, 790), fill=(174, 244, 244, 95), width=3)
    return im.rotate(-9, expand=False, resample=Image.Resampling.BICUBIC)


def ImageChops_multiply(a: Image.Image, b: Image.Image) -> Image.Image:
    # Keep PIL ImageChops isolated from public API.
    from PIL import ImageChops
    return ImageChops.multiply(a, b)


def _product_image(source: str | None, accent: str) -> Image.Image:
    if source is None:
        return _phone(accent)
    path = Path(source)
    if path.stat().st_size > 24*1024*1024:
        raise ValueError("Product image exceeds 24 MiB")
    with Image.open(path) as original:
        if original.width*original.height > 24_000_000:
            raise ValueError("Product image exceeds 24 megapixels")
        src = ImageOps.exif_transpose(original).convert("RGBA")
    # Contain rather than crop: user image stays visually intact.
    src.thumbnail((610, 880), Image.Resampling.LANCZOS)
    im = Image.new("RGBA", (700, 1020))
    im.alpha_composite(src, ((700-src.width)//2, (1020-src.height)//2))
    return im


def _asset(project: TTGProject, action: ActionEngine, root: Path,
           image: Image.Image, filename: str, name: str,
           x: int, y: int, scale: float) -> None:
    path = root/"assets"/filename
    image.save(path, "PNG", optimize=True)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    project.assets.append(Asset(id=new_id("asset"), kind="image", name=name,
                                path="assets/"+filename, sha256=digest, required=True))
    layer = action.add_image(project, "assets/"+filename, x, y, name)
    layer.transform.scale_x = layer.transform.scale_y = scale
    layer.locked = False


def _shape(project: TTGProject, action: ActionEngine, name: str,
           x: int, y: int, w: int, h: int, fill: str,
           radius: int = 0, outline: str | None = None) -> None:
    layer = action.add_shape(project, "rectangle", x, y)
    layer.name = name
    layer.properties.update(width=w, height=h, fill=fill, radius=radius)
    if outline:
        layer.properties["outline"] = outline


def _wrap_words(text: str, font: ImageFont.ImageFont, maximum: int,
                measure: ImageDraw.ImageDraw) -> str:
    lines: list[str] = []
    for paragraph in text.replace("\\n", "\n").split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if current and measure.textbbox((0, 0), candidate, font=font)[2] > maximum:
                lines.append(current)
                current = word
            else:
                current = candidate
        lines.append(current)
    return "\n".join(lines)


def _text(project: TTGProject, action: ActionEngine, name: str, words: str,
          x: int, y: int, size: int, color: str, *,
          bold: bool = True, max_width: int | None = None,
          min_size: int = 17, spacing: int = 4,
          wrap: bool = False, max_height: int | None = None) -> None:
    selected = words.replace("\\n", "\n")
    if max_width is not None:
        measure = ImageDraw.Draw(Image.new("L", (1, 1)))
        for proposed in range(size, min(min_size, size) - 1, -1):
            font = load_font("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", proposed)
            value = _wrap_words(words, font, max_width, measure) if wrap else selected
            bbox = measure.multiline_textbbox((0, 0), value, font=font, spacing=spacing)
            line_count = value.count("\n") + 1
            if (bbox[2] - bbox[0] <= max_width and
                (max_height is None or bbox[3] - bbox[1] <= max_height) and
                (not wrap or line_count <= 3)):
                selected, size = value, proposed
                break
        else:
            raise ValueError(f"Text '{name}' does not fit the selected canvas")
    layer = action.add_text(project, selected, x, y, name)
    layer.properties.update(
        text=selected, size=size, color=color, spacing=spacing,
        font_path="DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    )

def _layout(project: TTGProject, brief: CampaignBrief, a: ActionEngine,
            root: Path, w: int, h: int, accent: str) -> None:
    _asset(project, a, root, _backdrop(w, h, accent), "backdrop.png",
           "Atmospheric background", 0, 0, 1)
    if brief.layout == "flagship":
        _asset(project, a, root, _rings(780, 780, accent), "orbit.png",
               "Editable orbit element", 275, 438, .98)
        _asset(project, a, root, _product_image(brief.image_path, accent),
               "product.png", "Replaceable hero product", 405, 455, .85)
        _shape(project, a, "Top separator", 70, 145, 940, 2, "#355168")
        _text(project, a, "Brand", brief.brand, 70, 57, 32, "#F4FCFF", max_width=680)
        _text(project, a, "Edition", "CREATIVE / 001", 812, 69, 17, accent, max_width=225)
        _text(project, a, "Category", "THE NEXT CHAPTER   /   PRODUCT EXPERIENCE",
              73, 188, 17, accent, bold=False, max_width=914)
        _text(project, a, "Hero headline", brief.headline.upper(), 67, 242,
              85, "#F8FDFF", max_width=965, min_size=32, wrap=True, max_height=115)
        _text(project, a, "Hero subhead", brief.subhead, 73, 427, 22,
              "#BDD1DF", bold=False, max_width=435,
              min_size=18, wrap=True, max_height=88)
        _shape(project, a, "Story accent", 76, 806, 3, 278, accent)
        _text(project, a, "Product name", brief.product_name.upper(), 99, 814, 28,
              "#FFFFFF", max_width=455)
        _text(project, a, "Quality note", "01 / DESIGN WITHOUT LIMITS", 100, 864,
              17, accent, max_width=410)
        _text(project, a, "Value", "YOUR VISION.\nMADE REAL.", 97, 919,
              41, "#F2FAFC", max_width=370)
        _shape(project, a, "Call to action tile", 70, 1155, 398, 62,
               "#113544", radius=19, outline=accent)
        _text(project, a, "Call to action", brief.cta.upper(), 92, 1167,
              23, "#EFFFFF", max_width=360)
        _shape(project, a, "Bottom divider", 71, 1244, 938, 2, "#355168")
        _text(project, a, "Website", brief.website, 72, 1260, 25,
              "#F6FCFF", bold=False, max_width=690)
        _text(project, a, "Series", "ONE BRAND  /  ALL SOLUTIONS", 693, 1270,
              16, accent, max_width=305)
    elif brief.layout == "social":
        _asset(project, a, root, _rings(760, 760, accent), "orbit.png",
               "Editable orbit element", 235, 245, .95)
        _asset(project, a, root, _product_image(brief.image_path, accent),
               "product.png", "Replaceable hero product", 404, 274, .72)
        _text(project, a, "Brand", brief.brand, 64, 56, 29, "#FFFFFF", max_width=750)
        _text(project, a, "Edition", "STUDIO / SOCIAL", 795, 63, 17, accent, max_width=220)
        _shape(project, a, "Header rule", 66, 122, 948, 2, "#355168")
        _text(project, a, "Hero headline", brief.headline.upper(), 64, 172, 72,
              "#F7FDFF", max_width=955, min_size=30, wrap=True, max_height=98)
        _text(project, a, "Hero subhead", brief.subhead, 68, 349, 20,
              "#C7D8E5", bold=False, max_width=410,
              min_size=18, wrap=True, max_height=82)
        _shape(project, a, "Product label tile", 63, 754, 460, 86,
               "#123042", radius=20, outline="#3C6975")
        _text(project, a, "Product name", brief.product_name.upper(), 83, 779,
              25, "#FFFFFF", max_width=428)
        _shape(project, a, "CTA tile", 63, 861, 350, 58, "#164957", radius=18, outline=accent)
        _text(project, a, "Call to action", brief.cta.upper(), 84, 872, 21,
              "#FFFFFF", max_width=307)
        _shape(project, a, "Footer rule", 66, 978, 949, 2, "#355168")
        _text(project, a, "Website", brief.website, 66, 995, 24,
              "#FFFFFF", bold=False, max_width=666)
        _text(project, a, "Series", "ONE BRAND. ALL SOLUTIONS.", 750, 1001,
              14, accent, max_width=280)
    else:
        _asset(project, a, root, _rings(960, 960, accent), "orbit.png",
               "Editable orbit element", 925, 45, .97)
        _asset(project, a, root, _product_image(brief.image_path, accent),
               "product.png", "Replaceable hero product", 1140, 70, .92)
        _text(project, a, "Brand", brief.brand, 95, 65, 38, "#FFFFFF", max_width=1050)
        _text(project, a, "Edition", "CREATIVE STUDIO   /   LAUNCH SERIES",
              1433, 85, 17, accent, max_width=430)
        _shape(project, a, "Header rule", 96, 145, 1725, 2, "#355168")
        _text(project, a, "Category", "ONE BRAND. ALL SOLUTIONS.", 101, 227,
              23, accent, max_width=905)
        _text(project, a, "Hero headline", brief.headline.upper(), 91, 323,
              87, "#FCFEFF", max_width=975, min_size=32, wrap=True, max_height=135)
        _text(project, a, "Hero subhead", brief.subhead, 99, 525,
              27, "#C0D6E2", bold=False, max_width=800,
              min_size=20, wrap=True, max_height=76)
        _shape(project, a, "Accent rule", 104, 640, 105, 5, accent, radius=2)
        _text(project, a, "Product name", brief.product_name.upper(), 101, 681,
              32, "#FFFFFF", max_width=890)
        _shape(project, a, "CTA tile", 99, 776, 440, 80,
               "#154451", radius=22, outline=accent)
        _text(project, a, "Call to action", brief.cta.upper(), 129, 794,
              28, "#F8FFFF", max_width=380)
        _shape(project, a, "Footer rule", 102, 950, 1725, 2, "#355168")
        _text(project, a, "Website", brief.website, 105, 976, 27,
              "#FFFFFF", bold=False, max_width=1150)
        _text(project, a, "Series", "THETECHGUY / CREATIVE", 1460, 980,
              19, accent, max_width=390)


def compose_campaign(brief: CampaignBrief, output_dir: str | Path) -> dict[str, Path]:
    """Create a relocatable native project, PNG and integrity-checked ZIP.

    The output directory must be new or empty, never an existing project.
    """
    brief.validate()
    output = Path(output_dir).resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError("Refusing to overwrite a nonempty campaign directory")
    output.mkdir(parents=True, exist_ok=True)
    (output/"assets").mkdir(exist_ok=True)
    _, w, h = FORMATS[brief.layout]
    a = ActionEngine()
    project = a.new_project(f"{brief.brand} — {brief.headline}", "image")
    project.canvas.width, project.canvas.height = w, h
    project.canvas.background = "#070D19"
    project.export = {"format": "png", "resolution": f"{w}x{h}",
                      "quality": "lossless", "generator": "manual_procedural_studio"}
    _layout(project, brief, a, output, w, h, _ACCENTS[brief.accent])
    errors = [x.message for x in ProjectValidator().validate(project, output)
              if x.level == "error"]
    if errors:
        raise ValueError("Generated project invalid: " + "; ".join(errors))
    project_path = output/"campaign.ttgstudio.json"
    project.save(project_path)
    preview_path = output/"campaign.png"
    ExportService(output).export_png(project, preview_path)
    reopened = TTGProject.load(project_path)
    replay = CanvasRenderer(RenderContext(output)).render(reopened)
    with Image.open(preview_path) as saved:
        if replay.tobytes() != saved.convert("RGBA").tobytes():
            raise RuntimeError("Editable project replay differs from exported PNG")
    manifest = {
        "schema": "ttg.creative.campaign.v1",
        "generator": "offline_manual_procedural_not_ai",
        "layout": brief.layout, "canvas": [w, h], "layer_count": len(reopened.layers),
        "brief": {k: v for k, v in vars(brief).items() if k != "image_path"},
        "sha256": {},
    }
    files = [project_path, preview_path, *sorted((output/"assets").glob("*.png"))]
    for file in files:
        manifest["sha256"][file.relative_to(output).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    manifest_path = output/"manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    zip_path = output/"portable-campaign.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in [*files, manifest_path]:
            archive.write(file, file.relative_to(output).as_posix())
    return {"project": project_path, "preview": preview_path, "bundle": zip_path,
            "manifest": manifest_path}
