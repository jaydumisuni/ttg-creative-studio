#!/usr/bin/env python3
"""Reference-quality procedural still renderer for the THETECHGUY intro.

This module exists for the current product milestone: first make the repo produce
an acceptable still frame, then move to motion/video. It does not pretend to be a
full 3D renderer yet; it produces a premium 2.5D neon composition using Pillow.
"""

from __future__ import annotations

from pathlib import Path
import math
import random
from PIL import Image, ImageDraw, ImageFilter

from ttg_canvas_engine import RenderContext
from ttg_intro_builder import IntroBuilder
from ttg_text_renderer import render_text_layer


CYAN = "#00E5FF"
PURPLE = "#BC13FE"
BLUE = "#2368FF"
WHITE = "#F7FAFF"
DARK = "#03040E"


class ReferenceStillRenderer:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.context = RenderContext(self.project_root)

    def render(self, width: int = 1920, height: int = 1080) -> Image.Image:
        img = Image.new("RGBA", (width, height), DARK)
        self._background(img)
        self._floor(img)
        self._particles(img)
        self._energy_ring(img)
        self._service_cards(img)
        self._ghost(img)
        self._wordmark(img)
        self._subtitle_tagline(img)
        self._vignette(img)
        return img

    def _background(self, img: Image.Image) -> None:
        draw = ImageDraw.Draw(img)
        w, h = img.size
        for i in range(110):
            x = int((i * 67) % w)
            y = int((i * 139) % int(h * 0.75))
            length = 70 + (i % 9) * 22
            color = PURPLE if i % 2 else CYAN
            draw.line((x, y, x + (i % 5 - 2) * 8, y + length), fill=color + "33", width=2)
        for i in range(28):
            y = int(h * 0.48 + i * 15)
            draw.line((0, y, w, y + int(i * 2.2)), fill="#11266A44", width=1)

    def _floor(self, img: Image.Image) -> None:
        draw = ImageDraw.Draw(img)
        w, h = img.size
        horizon = int(h * 0.58)
        for i in range(38):
            x = int((i / 37) * w)
            draw.line((w // 2, horizon, x, h), fill=(CYAN if i % 2 else PURPLE) + "44", width=2)
        for j in range(18):
            t = j / 17
            y = int(horizon + (t ** 1.9) * (h - horizon))
            draw.line((0, y, w, y), fill="#1C38A844", width=2)

    def _particles(self, img: Image.Image) -> None:
        draw = ImageDraw.Draw(img)
        w, h = img.size
        rng = random.Random(49)
        for i in range(520):
            x = int(rng.random() * w)
            y = int(rng.random() * h)
            r = 1 + (i % 4)
            color = [CYAN, PURPLE, BLUE][i % 3]
            draw.ellipse((x, y, x + r, y + r), fill=color + "AA")

    def _energy_ring(self, img: Image.Image) -> None:
        ring = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(ring)
        cx, cy = img.size[0] // 2, 430
        for i in range(34):
            box = (cx - 350 - i * 3, cy - 92 - i, cx + 350 + i * 3, cy + 92 + i)
            color = PURPLE if i % 2 else CYAN
            draw.arc(box, start=195 + i, end=345 - i, fill=color + "99", width=4)
            draw.arc(box, start=15 + i, end=165 - i, fill=color + "55", width=3)
        ring = ring.filter(ImageFilter.GaussianBlur(1.2))
        img.alpha_composite(ring)

    def _ghost(self, img: Image.Image) -> None:
        path = self.project_root / "resources" / "logo.png"
        if not path.exists():
            return
        ghost = Image.open(path).convert("RGBA")
        ghost.thumbnail((450, 450), Image.Resampling.LANCZOS)
        x = (img.size[0] - ghost.width) // 2
        y = 72
        glow = ghost.filter(ImageFilter.GaussianBlur(18))
        img.alpha_composite(glow, (x, y))
        img.alpha_composite(ghost, (x, y))

    def _service_cards(self, img: Image.Image) -> None:
        cards = [("SYSTEMS", 145, 150, PURPLE), ("TOOLS", 500, 195, PURPLE), ("ISP", 1270, 195, CYAN), ("WEB", 1585, 150, CYAN)]
        for label, x, y, color in cards:
            self._card(img, label, x, y, color)

    def _card(self, img: Image.Image, label: str, x: int, y: int, color: str) -> None:
        card = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)
        box = (x, y, x + 245, y + 245)
        for i in range(8):
            draw.rounded_rectangle((box[0]-i*3, box[1]-i*3, box[2]+i*3, box[3]+i*3), radius=24, outline=color + "33", width=2)
        draw.rounded_rectangle(box, radius=24, fill="#07132F66", outline=color, width=4)
        icon_y = y + 58
        if label in {"ISP", "WEB"}:
            draw.ellipse((x+73, icon_y, x+172, icon_y+99), outline=color, width=4)
            draw.line((x+123, icon_y, x+123, icon_y+99), fill=color, width=3)
            draw.arc((x+87, icon_y, x+158, icon_y+99), 90, 270, fill=color, width=3)
            draw.arc((x+87, icon_y, x+158, icon_y+99), -90, 90, fill=color, width=3)
            draw.line((x+80, icon_y+50, x+165, icon_y+50), fill=color, width=3)
        elif label == "TOOLS":
            draw.line((x+78, icon_y+20, x+160, icon_y+102), fill=color, width=10)
            draw.line((x+160, icon_y+20, x+78, icon_y+102), fill=color, width=10)
        else:
            pts = [(x+123, icon_y+12), (x+72, icon_y+52), (x+92, icon_y+112), (x+154, icon_y+112), (x+174, icon_y+52)]
            draw.line(pts + [pts[0]], fill=color, width=4)
            for px, py in pts:
                draw.ellipse((px-8, py-8, px+8, py+8), outline=color, width=3)
        card = card.filter(ImageFilter.GaussianBlur(0.3))
        img.alpha_composite(card)
        text = render_text_layer(img.size, label, x + 42, y + 168, {"size": 39, "color": WHITE, "glow": True, "glow_blur": 7, "stroke_width": 1, "stroke_fill": "#140022"})
        img.alpha_composite(text)

    def _wordmark(self, img: Image.Image) -> None:
        text = "THETECHGUY"
        props = {
            "size": 178,
            "gradient": True,
            "gradient_start": PURPLE,
            "gradient_end": CYAN,
            "stroke_width": 4,
            "stroke_fill": "#16002F",
            "shadow": True,
            "shadow_blur": 10,
            "glow": True,
            "glow_blur": 12,
            "glow_alpha": 0.9,
        }
        x, y = 180, 595
        for offset in range(35, 0, -4):
            ex = dict(props)
            ex["gradient"] = False
            ex["color"] = "#170033"
            ex["glow"] = False
            ex["shadow"] = False
            img.alpha_composite(render_text_layer(img.size, text, x + offset, y + offset, ex))
        main = render_text_layer(img.size, text, x, y, props)
        img.alpha_composite(main)
        bbox = main.getbbox()
        if bbox:
            crop = main.crop(bbox).transpose(Image.Transpose.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(8))
            alpha = crop.getchannel("A").point(lambda p: int(p * 0.25))
            crop.putalpha(alpha)
            img.alpha_composite(crop, (bbox[0], bbox[3] + 8))

    def _subtitle_tagline(self, img: Image.Image) -> None:
        img.alpha_composite(render_text_layer(img.size, "D I G I T A L   S O L U T I O N S", 440, 805, {"size": 58, "color": WHITE, "glow": True, "glow_blur": 7, "spacing": 8}))
        img.alpha_composite(render_text_layer(img.size, "Fairytale Business — Make a wish, we sort it.", 445, 920, {"size": 38, "color": WHITE, "glow": True, "glow_blur": 5}))
        img.alpha_composite(render_text_layer(img.size, "thetechguyds.com", 680, 990, {"size": 42, "color": "#EAF3FF", "glow": True, "glow_color": PURPLE, "glow_blur": 9}))

    def _vignette(self, img: Image.Image) -> None:
        w, h = img.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((-w * 0.08, -h * 0.18, w * 1.08, h * 1.18), fill=230)
        mask = Image.eval(mask.filter(ImageFilter.GaussianBlur(90)), lambda p: 255 - p)
        vignette = Image.new("RGBA", (w, h), (0, 0, 0, 150))
        vignette.putalpha(mask)
        img.alpha_composite(vignette)


def render_reference_still(project_root: str | Path, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ReferenceStillRenderer(project_root).render().convert("RGB").save(output, quality=95)
    return output
