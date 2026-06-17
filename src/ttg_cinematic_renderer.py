#!/usr/bin/env python3
"""Cinematic 2.5D renderer for TTG Creative Studio.

This is the bridge between flat 2D preview and a future true 3D backend.
It creates depth, extrusion, glow, particles and camera-feel using Pillow.
"""

from __future__ import annotations

from pathlib import Path
import math
import random
from PIL import Image, ImageDraw, ImageFilter

from ttg_project_schema import TTGProject
from ttg_timeline_engine import TimelineEngine
from ttg_text_renderer import render_text_layer


class CinematicRenderer:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.timeline = TimelineEngine()

    def render_frame(self, project: TTGProject, time: float = 0.0) -> Image.Image:
        canvas = Image.new("RGBA", (project.canvas.width, project.canvas.height), project.canvas.background)
        self._draw_background_energy(canvas, time)
        for raw in project.layers:
            if not raw.visible:
                continue
            layer = self.timeline.apply_to_layer(raw, time)
            if layer.type in {"text", "text3d"}:
                self._draw_cinematic_text(canvas, layer, time)
            elif layer.type == "particle":
                self._draw_particles(canvas, layer, time)
            elif layer.type == "shape":
                self._draw_shape(canvas, layer)
        self._draw_vignette(canvas)
        return canvas

    def _draw_cinematic_text(self, canvas: Image.Image, layer, time: float) -> None:
        text = str(layer.properties.get("text", layer.name))
        props = dict(layer.properties)
        props.setdefault("shadow", True)
        props.setdefault("glow", True)
        props.setdefault("stroke_width", 1 if layer.type == "text3d" else 0)
        props.setdefault("stroke_fill", "#00111F")
        depth = int(props.get("extrude_px", 14 if layer.type == "text3d" else 0))
        for offset in range(depth, 0, -2):
            extrude_props = dict(props)
            extrude_props["color"] = props.get("extrude_color", "#24004A")
            extrude_props["glow"] = False
            extrude_props["shadow"] = False
            img = render_text_layer(canvas.size, text, layer.transform.x + offset, layer.transform.y + offset, extrude_props)
            canvas.alpha_composite(img)
        img = render_text_layer(canvas.size, text, layer.transform.x, layer.transform.y, props)
        if layer.transform.opacity < 1:
            img.putalpha(img.getchannel("A").point(lambda p: int(p * layer.transform.opacity)))
        canvas.alpha_composite(img)

    def _draw_background_energy(self, canvas: Image.Image, time: float) -> None:
        draw = ImageDraw.Draw(canvas)
        w, h = canvas.size
        for i in range(26):
            angle = (i / 26) * math.tau + time * 0.18
            x1 = w / 2 + math.cos(angle) * 70
            y1 = h / 2 + math.sin(angle) * 40
            x2 = w / 2 + math.cos(angle) * w
            y2 = h / 2 + math.sin(angle) * h
            color = "#00E5FF44" if i % 2 == 0 else "#BC13FE44"
            draw.line((x1, y1, x2, y2), fill=color, width=2)

    def _draw_particles(self, canvas: Image.Image, layer, time: float) -> None:
        draw = ImageDraw.Draw(canvas)
        colors = layer.properties.get("colors", ["#00E5FF", "#BC13FE"])
        density = int(layer.properties.get("density", 140))
        w, h = canvas.size
        rng = random.Random(49)
        for i in range(min(density, 400)):
            base_x = rng.random() * w
            base_y = rng.random() * h
            drift = time * (20 + (i % 11))
            x = (base_x + drift) % w
            y = (base_y + math.sin(time + i) * 8) % h
            r = 1 + (i % 4)
            draw.ellipse((x, y, x + r, y + r), fill=colors[i % len(colors)])

    def _draw_shape(self, canvas: Image.Image, layer) -> None:
        draw = ImageDraw.Draw(canvas)
        x, y = layer.transform.x, layer.transform.y
        width = float(layer.properties.get("width", 200)) * layer.transform.scale_x
        height = float(layer.properties.get("height", 100)) * layer.transform.scale_y
        fill = layer.properties.get("fill", "#00E5FF")
        draw.rounded_rectangle((x, y, x + width, y + height), radius=18, fill=fill)

    def _draw_vignette(self, canvas: Image.Image) -> None:
        w, h = canvas.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((-w * 0.15, -h * 0.25, w * 1.15, h * 1.25), fill=220)
        mask = Image.eval(mask.filter(ImageFilter.GaussianBlur(80)), lambda p: 255 - p)
        vignette = Image.new("RGBA", (w, h), (0, 0, 0, 150))
        vignette.putalpha(mask)
        canvas.alpha_composite(vignette)
