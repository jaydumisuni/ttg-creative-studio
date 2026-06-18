#!/usr/bin/env python3
"""Reference-quality procedural still renderer for the THETECHGUY intro.

Current milestone: make the repo itself create a premium still frame before
moving to final video. This is a 2.5D neon compositor using Pillow, with strong
brand staging, glass cards, light beams, floor depth, bloom and reflections.
"""

from __future__ import annotations

from pathlib import Path
import math
import random
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from ttg_canvas_engine import RenderContext
from ttg_text_renderer import render_text_layer

CYAN = "#00E5FF"
PURPLE = "#BC13FE"
BLUE = "#2368FF"
WHITE = "#F7FAFF"
DARK = "#03040E"
PINK = "#FF4DFF"


class ReferenceStillRenderer:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.context = RenderContext(self.project_root)

    def render(self, width: int = 1920, height: int = 1080) -> Image.Image:
        img = Image.new("RGBA", (width, height), DARK)
        self._background_gradient(img)
        self._background(img)
        self._light_beams(img)
        self._floor(img)
        self._particles(img)
        self._energy_ring(img)
        self._service_cards(img)
        self._ghost(img)
        self._wordmark(img)
        self._subtitle_tagline(img)
        self._foreground_sweep(img)
        self._vignette(img)
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = ImageEnhance.Sharpness(img).enhance(1.08)
        return img

    def _background_gradient(self, img: Image.Image) -> None:
        w, h = img.size
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        for y in range(h):
            t = y / max(1, h - 1)
            r = int(3 + 12 * (1 - t))
            g = int(4 + 8 * (1 - t))
            b = int(14 + 42 * (1 - t))
            draw.line((0, y, w, y), fill=(r, g, b, 255))
        img.alpha_composite(layer)

    def _background(self, img: Image.Image) -> None:
        draw = ImageDraw.Draw(img)
        w, h = img.size
        for i in range(180):
            x = int((i * 67) % w)
            y = int((i * 139) % int(h * 0.78))
            length = 60 + (i % 11) * 24
            color = [PURPLE, CYAN, BLUE][i % 3]
            draw.line((x, y, x + (i % 7 - 3) * 9, y + length), fill=color + "30", width=2)
        for i in range(44):
            y = int(h * 0.44 + i * 12)
            draw.line((0, y, w, y + int(i * 2.4)), fill="#11266A38", width=1)

    def _light_beams(self, img: Image.Image) -> None:
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        w, h = img.size
        center = w // 2
        for i, color in enumerate([PURPLE, CYAN, BLUE, PINK]):
            offset = (i - 1.5) * 110
            poly = [(center + offset, 120), (center + offset - 520, h), (center + offset + 520, h)]
            draw.polygon(poly, fill=color + "18")
        layer = layer.filter(ImageFilter.GaussianBlur(28))
        img.alpha_composite(layer)

    def _floor(self, img: Image.Image) -> None:
        floor = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(floor)
        w, h = img.size
        horizon = int(h * 0.58)
        for i in range(52):
            x = int((i / 51) * w)
            draw.line((w // 2, horizon, x, h), fill=(CYAN if i % 2 else PURPLE) + "4A", width=2)
        for j in range(22):
            t = j / 21
            y = int(horizon + (t ** 1.85) * (h - horizon))
            draw.line((0, y, w, y), fill="#1C38A850", width=2)
        floor = floor.filter(ImageFilter.GaussianBlur(0.4))
        img.alpha_composite(floor)

    def _particles(self, img: Image.Image) -> None:
        draw = ImageDraw.Draw(img)
        w, h = img.size
        rng = random.Random(49)
        for i in range(780):
            x = int(rng.random() * w)
            y = int(rng.random() * h)
            r = 1 + (i % 4)
            color = [CYAN, PURPLE, BLUE, PINK][i % 4]
            alpha = "AA" if y < h * 0.68 else "66"
            draw.ellipse((x, y, x + r, y + r), fill=color + alpha)
            if i % 33 == 0:
                draw.line((x - 18, y, x + 18, y), fill=color + "55", width=1)

    def _energy_ring(self, img: Image.Image) -> None:
        ring = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(ring)
        cx, cy = img.size[0] // 2, 432
        for i in range(46):
            box = (cx - 390 - i * 3, cy - 104 - i, cx + 390 + i * 3, cy + 104 + i)
            color = [PURPLE, CYAN, BLUE][i % 3]
            draw.arc(box, start=195 + i, end=345 - i, fill=color + "9A", width=4)
            draw.arc(box, start=15 + i, end=165 - i, fill=color + "5F", width=3)
        for i in range(18):
            angle = math.radians(i * 20)
            x = int(cx + math.cos(angle) * 430)
            y = int(cy + math.sin(angle) * 110)
            draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=CYAN + "CC")
        ring = ring.filter(ImageFilter.GaussianBlur(1.2))
        img.alpha_composite(ring)

    def _ghost(self, img: Image.Image) -> None:
        path = self.project_root / "resources" / "logo.png"
        if not path.exists():
            self._ghost_placeholder(img)
            return
        ghost = Image.open(path).convert("RGBA")
        ghost.thumbnail((470, 470), Image.Resampling.LANCZOS)
        x = (img.size[0] - ghost.width) // 2
        y = 58
        aura = Image.new("RGBA", img.size, (0, 0, 0, 0))
        for blur, alpha in [(34, 0.25), (18, 0.42), (8, 0.35)]:
            glow = ghost.filter(ImageFilter.GaussianBlur(blur))
            glow.putalpha(glow.getchannel("A").point(lambda p, a=alpha: int(p * a)))
            aura.alpha_composite(glow, (x, y))
        img.alpha_composite(aura)
        img.alpha_composite(ghost, (x, y))

    def _ghost_placeholder(self, img: Image.Image) -> None:
        draw = ImageDraw.Draw(img)
        cx, cy = img.size[0] // 2, 260
        draw.rounded_rectangle((cx - 120, cy - 135, cx + 120, cy + 135), radius=80, outline=CYAN, width=6)
        draw.text((cx - 45, cy - 25), "TTG", fill=WHITE)

    def _service_cards(self, img: Image.Image) -> None:
        cards = [("SYSTEMS", 138, 140, PURPLE), ("TOOLS", 492, 188, PURPLE), ("ISP", 1284, 188, CYAN), ("WEB", 1590, 140, CYAN)]
        for label, x, y, color in cards:
            self._card(img, label, x, y, color)

    def _card(self, img: Image.Image, label: str, x: int, y: int, color: str) -> None:
        card = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)
        box = (x, y, x + 250, y + 250)
        for i in range(12):
            draw.rounded_rectangle((box[0]-i*3, box[1]-i*3, box[2]+i*3, box[3]+i*3), radius=28, outline=color + "2D", width=2)
        draw.rounded_rectangle(box, radius=28, fill="#07132F80", outline=color, width=4)
        draw.line((x + 18, y + 28, x + 232, y + 28), fill=WHITE + "33", width=2)
        icon_y = y + 60
        if label in {"ISP", "WEB"}:
            draw.ellipse((x+73, icon_y, x+177, icon_y+104), outline=color, width=4)
            draw.line((x+125, icon_y, x+125, icon_y+104), fill=color, width=3)
            draw.arc((x+88, icon_y, x+162, icon_y+104), 90, 270, fill=color, width=3)
            draw.arc((x+88, icon_y, x+162, icon_y+104), -90, 90, fill=color, width=3)
            draw.line((x+80, icon_y+52, x+170, icon_y+52), fill=color, width=3)
        elif label == "TOOLS":
            draw.line((x+76, icon_y+20, x+164, icon_y+108), fill=color, width=10)
            draw.line((x+164, icon_y+20, x+76, icon_y+108), fill=color, width=10)
            draw.ellipse((x+109, icon_y+53, x+131, icon_y+75), outline=WHITE + "AA", width=3)
        else:
            pts = [(x+125, icon_y+10), (x+72, icon_y+54), (x+92, icon_y+116), (x+158, icon_y+116), (x+178, icon_y+54)]
            draw.line(pts + [pts[0]], fill=color, width=4)
            for px, py in pts:
                draw.ellipse((px-8, py-8, px+8, py+8), outline=color, width=3)
        glow = card.filter(ImageFilter.GaussianBlur(4))
        img.alpha_composite(glow)
        img.alpha_composite(card)
        text = render_text_layer(img.size, label, x + 36, y + 170, {"size": 40, "color": WHITE, "glow": True, "glow_blur": 8, "stroke_width": 1, "stroke_fill": "#140022"})
        img.alpha_composite(text)

    def _wordmark(self, img: Image.Image) -> None:
        text = "THETECHGUY"
        props = {
            "size": 188,
            "gradient": True,
            "gradient_start": PURPLE,
            "gradient_end": CYAN,
            "stroke_width": 5,
            "stroke_fill": "#120026",
            "shadow": True,
            "shadow_blur": 12,
            "glow": True,
            "glow_color": CYAN,
            "glow_blur": 14,
            "glow_alpha": 0.85,
        }
        x, y = 145, 590
        for offset in range(46, 0, -4):
            ex = dict(props)
            ex["gradient"] = False
            ex["color"] = "#150032"
            ex["glow"] = False
            ex["shadow"] = False
            img.alpha_composite(render_text_layer(img.size, text, x + offset, y + offset, ex))
        main = render_text_layer(img.size, text, x, y, props)
        img.alpha_composite(main)
        bbox = main.getbbox()
        if bbox:
            crop = main.crop(bbox).transpose(Image.Transpose.FLIP_TOP_BOTTOM).filter(ImageFilter.GaussianBlur(8))
            alpha = crop.getchannel("A").point(lambda p: int(p * 0.23))
            crop.putalpha(alpha)
            img.alpha_composite(crop, (bbox[0], bbox[3] + 10))

    def _subtitle_tagline(self, img: Image.Image) -> None:
        img.alpha_composite(render_text_layer(img.size, "D I G I T A L   S O L U T I O N S", 430, 812, {"size": 58, "color": WHITE, "glow": True, "glow_blur": 8, "spacing": 8}))
        img.alpha_composite(render_text_layer(img.size, "Fairytale Business — Make a wish, we sort it.", 438, 922, {"size": 38, "color": WHITE, "glow": True, "glow_blur": 5}))
        img.alpha_composite(render_text_layer(img.size, "thetechguyds.com", 680, 990, {"size": 42, "color": "#EAF3FF", "glow": True, "glow_color": PURPLE, "glow_blur": 10}))

    def _foreground_sweep(self, img: Image.Image) -> None:
        sweep = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(sweep)
        w, h = img.size
        for i in range(6):
            y = int(h * 0.72 + i * 42)
            draw.line((-120, y + 80, w + 120, y - 80), fill=(CYAN if i % 2 else PURPLE) + "22", width=5)
        sweep = sweep.filter(ImageFilter.GaussianBlur(7))
        img.alpha_composite(sweep)

    def _vignette(self, img: Image.Image) -> None:
        w, h = img.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((-w * 0.08, -h * 0.18, w * 1.08, h * 1.18), fill=232)
        mask = Image.eval(mask.filter(ImageFilter.GaussianBlur(90)), lambda p: 255 - p)
        vignette = Image.new("RGBA", (w, h), (0, 0, 0, 145))
        vignette.putalpha(mask)
        img.alpha_composite(vignette)


def render_reference_still(project_root: str | Path, output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    ReferenceStillRenderer(project_root).render().convert("RGB").save(output, quality=95)
    return output
