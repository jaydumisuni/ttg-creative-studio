#!/usr/bin/env python3
"""Repo-native motion preview renderer for the THETECHGUY reference intro.

This only runs after still verification. It creates proof frames first; MP4 can be
built later from these frames once the still and sequence direction are approved.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter

from ttg_reference_still_renderer import ReferenceStillRenderer


class ReferenceMotionRenderer:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.still_renderer = ReferenceStillRenderer(project_root)

    def render_frames(self, output_dir: str | Path, frames: int = 48, width: int = 1280, height: int = 720) -> list[Path]:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        base = self.still_renderer.render(1920, 1080)
        result: list[Path] = []
        for index in range(frames):
            t = index / max(1, frames - 1)
            # Camera-like push-in crop from slightly wide to full composition.
            margin_x = int(120 * (1 - t))
            margin_y = int(70 * (1 - t))
            crop = base.crop((margin_x, margin_y, 1920 - margin_x, 1080 - margin_y))
            frame = crop.resize((width, height), Image.Resampling.LANCZOS).convert("RGBA")

            # Startup glow ramp and slight bloom pulse.
            brightness = 0.58 + 0.42 * min(1.0, t * 1.6)
            contrast = 0.92 + 0.12 * t
            frame = ImageEnhance.Brightness(frame).enhance(brightness)
            frame = ImageEnhance.Contrast(frame).enhance(contrast)
            if index % 12 in {0, 1, 2}:
                glow = frame.filter(ImageFilter.GaussianBlur(3))
                frame = Image.blend(frame, glow, 0.10)

            path = output_dir / f"reference_frame_{index:04d}.jpg"
            frame.convert("RGB").save(path, quality=93)
            result.append(path)
        return result


def render_reference_motion_frames(project_root: str | Path, output_dir: str | Path, frames: int = 48) -> list[Path]:
    return ReferenceMotionRenderer(project_root).render_frames(output_dir, frames=frames)
