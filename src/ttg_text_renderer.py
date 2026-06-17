#!/usr/bin/env python3
"""Higher quality text rendering helpers for TTG Creative Studio."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont


def load_font(font_path: str | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path and Path(font_path).exists():
        return ImageFont.truetype(font_path, size)
    for candidate in ["arial.ttf", "segoeui.ttf", "calibri.ttf"]:
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            pass
    return ImageFont.load_default()


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
    draw_x = x
    if align == "center":
        draw_x = x - width / 2
    elif align == "right":
        draw_x = x - width

    if shadow:
        shadow_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_layer)
        sd.multiline_text((draw_x + 6, y + 6), text, font=font, fill=props.get("shadow_fill", "#000000AA"), spacing=spacing, stroke_width=stroke_width, stroke_fill=stroke_fill)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(float(props.get("shadow_blur", 6))))
        layer.alpha_composite(shadow_layer)

    text_layer = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    td = ImageDraw.Draw(text_layer)
    td.multiline_text((draw_x, y), text, font=font, fill=color, spacing=spacing, stroke_width=stroke_width, stroke_fill=stroke_fill)

    if glow:
        glow_layer = text_layer.filter(ImageFilter.GaussianBlur(float(props.get("glow_blur", 8))))
        glow_alpha = float(props.get("glow_alpha", 0.65))
        glow_layer.putalpha(glow_layer.getchannel("A").point(lambda p: int(p * glow_alpha)))
        layer.alpha_composite(glow_layer)

    layer.alpha_composite(text_layer)
    return layer
