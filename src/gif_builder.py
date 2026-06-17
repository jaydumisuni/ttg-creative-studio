#!/usr/bin/env python3
"""
Reusable loading GIF generator for TheTechGuy tools.
"""

from __future__ import annotations

import math
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps


PRESET_TEXT = {
    "Loading": "Loading",
    "Processing": "Processing",
    "Saving": "Saving",
    "Preparing AI": "Preparing AI",
}


@dataclass(slots=True)
class GifBuildOptions:
    source_path: str
    text: str = "Loading"
    preset: str = "Loading"
    width: int = 600
    height: int = 600
    fps: int = 18
    duration_seconds: float = 2.6
    glow_strength: float = 1.2
    pulse_strength: float = 0.11
    background: str = "transparent"
    ring_enabled: bool = True

    @property
    def frame_count(self) -> int:
        return max(16, int(round(self.fps * self.duration_seconds)))


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "bahnschrift.ttf",
        "arialbd.ttf",
        "arial.ttf",
        "segoeuib.ttf",
        "seguiemj.ttf",
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def normalized_options(options: GifBuildOptions) -> GifBuildOptions:
    return GifBuildOptions(
        source_path=options.source_path,
        text=(options.text or PRESET_TEXT.get(options.preset, "Loading")).strip() or "Loading",
        preset=options.preset or "Loading",
        width=max(128, int(options.width)),
        height=max(128, int(options.height)),
        fps=max(8, min(30, int(options.fps))),
        duration_seconds=max(1.2, float(options.duration_seconds)),
        glow_strength=max(0.0, float(options.glow_strength)),
        pulse_strength=max(0.0, float(options.pulse_strength)),
        background=options.background if options.background in {"transparent", "dark"} else "transparent",
        ring_enabled=bool(options.ring_enabled),
    )


def fit_logo(source_path: str, width: int, height: int) -> Image.Image:
    with Image.open(source_path) as opened:
        image = opened.convert("RGBA")
    target_size = int(min(width, height) * 0.42)
    return ImageOps.contain(image, (target_size, target_size), Image.Resampling.LANCZOS)


def add_neon_glow(base: Image.Image, colour: tuple[int, int, int], blur_radius: float) -> Image.Image:
    alpha = base.getchannel("A")
    glow_mask = alpha.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    glow = Image.new("RGBA", base.size, colour + (0,))
    glow.putalpha(glow_mask)
    return glow


def add_text_with_glow(
    canvas: Image.Image,
    text: str,
    box_width: int,
    baseline_y: int,
    frame_phase: float,
) -> None:
    font = load_font(max(22, box_width // 18))
    dots = "." * int((frame_phase * 4.0) % 4)
    content = f"{text}{dots}"

    temp = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(temp)
    bbox = draw.textbbox((0, 0), content, font=font)
    text_width = bbox[2] - bbox[0]
    x = (canvas.width - text_width) // 2
    y = baseline_y

    for offset_x, offset_y, fill in (
        (-2, 0, (255, 0, 222, 160)),
        (2, 0, (0, 209, 255, 160)),
        (0, 0, (246, 250, 255, 255)),
    ):
        draw.text((x + offset_x, y + offset_y), content, font=font, fill=fill)

    blur_radius = max(4, box_width // 48)
    glow = temp.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    canvas.alpha_composite(glow)
    canvas.alpha_composite(temp)


def draw_ring(canvas: Image.Image, center: tuple[int, int], diameter: int, phase: float) -> None:
    pulse = 0.88 + 0.18 * math.sin(phase * math.tau)
    radius = int(diameter * pulse * 0.58)
    ring = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(ring)
    cx, cy = center
    bounds = (cx - radius, cy - radius, cx + radius, cy + radius)
    alpha = int(105 + 65 * (0.5 + 0.5 * math.sin(phase * math.tau + math.pi / 2)))
    width = max(4, diameter // 36)
    draw.ellipse(bounds, outline=(67, 221, 255, alpha), width=width)
    ring = ring.filter(ImageFilter.GaussianBlur(radius=max(3, diameter // 42)))
    canvas.alpha_composite(ring)


def render_frame(options: GifBuildOptions, logo: Image.Image, frame_index: int) -> Image.Image:
    phase = frame_index / max(1, options.frame_count)
    pulse = 1.0 + options.pulse_strength * math.sin(phase * math.tau)

    canvas = Image.new(
        "RGBA",
        (options.width, options.height),
        (5, 8, 20, 255) if options.background == "dark" else (0, 0, 0, 0),
    )

    logo_size = (
        max(1, int(logo.width * pulse)),
        max(1, int(logo.height * pulse)),
    )
    scaled_logo = logo.resize(logo_size, Image.Resampling.LANCZOS)
    glow_radius = max(6.0, min(options.width, options.height) * 0.022 * (1.0 + options.glow_strength))

    glow_magenta = add_neon_glow(scaled_logo, (255, 25, 220), glow_radius)
    glow_cyan = add_neon_glow(scaled_logo, (0, 214, 255), glow_radius * 0.9)

    center_x = options.width // 2
    center_y = max(int(options.height * 0.34), scaled_logo.height // 2 + 24)
    x = center_x - scaled_logo.width // 2
    y = center_y - scaled_logo.height // 2

    if options.ring_enabled:
        draw_ring(canvas, (center_x, center_y), max(scaled_logo.width, scaled_logo.height), phase)

    canvas.alpha_composite(glow_magenta, (x - 3, y))
    canvas.alpha_composite(glow_cyan, (x + 3, y))
    canvas.alpha_composite(scaled_logo, (x, y))

    glow_orb = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    orb_draw = ImageDraw.Draw(glow_orb)
    orb_radius = max(4, options.width // 70)
    orb_offset = int(math.sin(phase * math.tau) * options.width * 0.06)
    orb_center = (center_x + orb_offset, y + scaled_logo.height + int(options.height * 0.04))
    orb_draw.ellipse(
        (
            orb_center[0] - orb_radius,
            orb_center[1] - orb_radius,
            orb_center[0] + orb_radius,
            orb_center[1] + orb_radius,
        ),
        fill=(79, 217, 255, 220),
    )
    glow_orb = glow_orb.filter(ImageFilter.GaussianBlur(radius=max(3, orb_radius)))
    canvas.alpha_composite(glow_orb)

    add_text_with_glow(
        canvas,
        PRESET_TEXT.get(options.preset, options.preset) if options.text.strip() == "" else options.text,
        options.width,
        int(options.height * 0.78),
        phase,
    )
    return canvas


def generate_loading_frames(options: GifBuildOptions) -> list[Image.Image]:
    resolved = normalized_options(options)
    logo = fit_logo(resolved.source_path, resolved.width, resolved.height)
    return [render_frame(resolved, logo, index) for index in range(resolved.frame_count)]


def gif_frame_from_rgba(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    frame = rgba.convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
    transparent_mask = Image.eval(alpha, lambda value: 255 if value <= 8 else 0)
    frame.paste(255, transparent_mask)
    frame.info["transparency"] = 255
    frame.info["disposal"] = 2
    return frame


def save_loading_gif(options: GifBuildOptions, output_path: str | Path) -> str:
    resolved = normalized_options(options)
    frames = generate_loading_frames(resolved)
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    gif_frames = [gif_frame_from_rgba(frame) for frame in frames]
    gif_frames[0].save(
        destination,
        format="GIF",
        save_all=True,
        append_images=gif_frames[1:],
        duration=max(20, int(round(1000 / resolved.fps))),
        loop=0,
        disposal=2,
        transparency=255,
        optimize=False,
    )
    return str(destination)


def build_preview_gif(options: GifBuildOptions) -> str:
    temp_dir = Path(tempfile.mkdtemp(prefix="thetechguy_gif_"))
    preview_path = temp_dir / "preview.gif"
    return save_loading_gif(options, preview_path)
