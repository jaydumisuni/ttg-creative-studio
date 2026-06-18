#!/usr/bin/env python3
"""Repo-native motion preview renderer for the THETECHGUY reference intro.

Creates proof frames with an actual staged reveal: dark startup, light sweep,
cards waking up, ghost/wordmark bloom and final lock. MP4 remains a later stage.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

from ttg_reference_still_renderer import CYAN, PURPLE, ReferenceStillRenderer


class ReferenceMotionRenderer:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.still_renderer = ReferenceStillRenderer(project_root)

    def _ease(self, t: float) -> float:
        t = max(0.0, min(1.0, t))
        return 1 - (1 - t) ** 3

    def _scanline_overlay(self, size: tuple[int, int], t: float) -> Image.Image:
        w, h = size
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        y = int((t * 1.35 % 1.0) * h)
        draw.rectangle((0, y - 12, w, y + 12), fill=CYAN + "18")
        draw.line((0, y, w, y), fill=PURPLE + "AA", width=2)
        for i in range(0, h, 16):
            draw.line((0, i, w, i), fill="#FFFFFF08", width=1)
        return layer.filter(ImageFilter.GaussianBlur(1.2))

    def _side_wipes(self, size: tuple[int, int], t: float) -> Image.Image:
        w, h = size
        layer = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        p = self._ease(min(1.0, t * 1.8))
        left = int(-w * 0.35 + w * 0.28 * p)
        right = int(w * 1.35 - w * 0.28 * p)
        draw.polygon([(left, 0), (left + 180, 0), (left + 80, h), (left - 100, h)], fill=PURPLE + "26")
        draw.polygon([(right, 0), (right - 180, 0), (right - 80, h), (right + 100, h)], fill=CYAN + "26")
        return layer.filter(ImageFilter.GaussianBlur(5))

    def render_frames(self, output_dir: str | Path, frames: int = 72, width: int = 1280, height: int = 720) -> list[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        base = self.still_renderer.render(1920, 1080)
        result: list[Path] = []
        for index in range(frames):
            t = index / max(1, frames - 1)
            p = self._ease(t)
            margin_x = int(150 * (1 - p))
            margin_y = int(86 * (1 - p))
            crop = base.crop((margin_x, margin_y, 1920 - margin_x, 1080 - margin_y))
            frame = crop.resize((width, height), Image.Resampling.LANCZOS).convert("RGBA")

            brightness = 0.42 + 0.62 * min(1.0, t * 1.35)
            contrast = 0.90 + 0.18 * p
            frame = ImageEnhance.Brightness(frame).enhance(brightness)
            frame = ImageEnhance.Contrast(frame).enhance(contrast)

            overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            overlay.alpha_composite(self._side_wipes(frame.size, t))
            overlay.alpha_composite(self._scanline_overlay(frame.size, t))
            if 0.18 < t < 0.34 or 0.58 < t < 0.70:
                glow = frame.filter(ImageFilter.GaussianBlur(4))
                frame = Image.blend(frame, glow, 0.16)
            frame.alpha_composite(overlay)

            # Brief blackout at the very start so it does not feel like a static zoom.
            if t < 0.08:
                alpha = int(255 * (1 - t / 0.08))
                dark = Image.new("RGBA", frame.size, (0, 0, 0, alpha))
                frame.alpha_composite(dark)

            path = output_dir / f"reference_frame_{index:04d}.jpg"
            frame.convert("RGB").save(path, quality=93)
            result.append(path)
        return result


def render_reference_motion_frames(project_root: str | Path, output_dir: str | Path, frames: int = 72) -> list[Path]:
    return ReferenceMotionRenderer(project_root).render_frames(output_dir, frames=frames)
