#!/usr/bin/env python3
"""Higher quality text rendering helpers for TTG Creative Studio."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def load_font(font_path: str | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path and Path(font_path).exists():
        return ImageFont.truetype(font_path, size)
    for candidate in ["arialbd.ttf", "arial.ttf", "segoeuib.ttf", "segoeui.ttf", "calibri.ttf"]:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _hex_to_rgb(value: str) -> tuple[int, int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) == 6:
        value += "FF"
    return tuple(int(value[i:i + 2], 16) for i in range(0, 8, 2))  # type: ignore[return-value]


def _gradient(size: tuple[int, int], start: str, end: str) -> Image.Image:
    width, height = size
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    s = _hex_to_rgb(start)
    e = _hex_to_rgb(end)
    draw = ImageDraw.Draw(img)
    for x in range(width):
        t = x / max(1, width - 1)
        color = tuple(int(s[i] * (1 - t) + e[i] * t) for i in range(4))
        draw.line((x, 0, x, height), fill=color)
    return img


def render_text_layer(canvas_size: tuple[int, int], text: str, x: float, y: float, props: dict) -> Image.Image:
    size = int(props.get("size", 72))
    font = load_font(props.get("font_path"), size)
    color = props.get("color", "#F7FAFF")
    stroke_width = int(props.get("stroke_width", 0))
    stroke_fill = props.get("stroke_fill", "#000000")
    shadow = bool(props.get("shadow", False))
    glow = bool(props.get("glow", False))
    align = props.get("align", "left")
    spacing = int(props.get("spacing", 4))

    layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, stroke_width=stroke_width)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    draw_x = x
    if align == "center":
        draw_x = x - width / 2
    elif align == "right":
        draw_x = x - width

    if shadow:
        shadow_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_layer)
        sd.multiline_text((draw_x + 8, y + 8), text, font=font, fill=props.get("shadow_fill", "#000000AA"), spacing=spacing, stroke_width=stroke_width, stroke_fill=stroke_fill)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(float(props.get("shadow_blur", 6))))
        layer.alpha_composite(shadow_layer)

    text_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    td = ImageDraw.Draw(text_layer)
    td.multiline_text((draw_x, y), text, font=font, fill=color, spacing=spacing, stroke_width=stroke_width, stroke_fill=stroke_fill)

    if props.get("gradient"):
        mask = text_layer.getchannel("A")
        grad = _gradient(canvas_size, props.get("gradient_start", "#BC13FE"), props.get("gradient_end", "#00E5FF"))
        grad.putalpha(mask)
        text_layer = grad
        if stroke_width:
            stroke_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            sd = ImageDraw.Draw(stroke_layer)
            sd.multiline_text((draw_x, y), text, font=font, fill=(0, 0, 0, 0), spacing=spacing, stroke_width=stroke_width, stroke_fill=stroke_fill)
            text_layer.alpha_composite(stroke_layer)

    if glow:
        glow_color = props.get("glow_color")
        glow_layer = text_layer
        if glow_color:
            alpha = text_layer.getchannel("A")
            glow_layer = Image.new("RGBA", canvas_size, _hex_to_rgb(glow_color))
            glow_layer.putalpha(alpha)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(float(props.get("glow_blur", 8))))
        glow_alpha = float(props.get("glow_alpha", 0.65))
        glow_layer.putalpha(glow_layer.getchannel("A").point(lambda p: int(p * glow_alpha)))
        layer.alpha_composite(glow_layer)

    layer.alpha_composite(text_layer)
    return layer
