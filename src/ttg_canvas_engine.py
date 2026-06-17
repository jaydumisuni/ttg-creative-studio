#!/usr/bin/env python3
"""2D canvas renderer for TTG Creative Studio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter

from ttg_project_schema import Layer, TTGProject
from ttg_text_renderer import render_text_layer


@dataclass
class RenderContext:
    project_root: Path
    asset_root: Path | None = None

    def resolve_asset(self, asset_path: str) -> Path:
        candidate = Path(asset_path)
        if candidate.is_absolute():
            return candidate
        if self.asset_root:
            return self.asset_root / asset_path
        return self.project_root / asset_path


class CanvasRenderer:
    def __init__(self, context: RenderContext):
        self.context = context

    def render(self, project: TTGProject, time: float = 0.0) -> Image.Image:
        canvas = Image.new("RGBA", (project.canvas.width, project.canvas.height), project.canvas.background)
        for layer in project.layers:
            if not layer.visible:
                continue
            self._draw_layer(canvas, layer, time=time)
        return canvas

    def _draw_layer(self, canvas: Image.Image, layer: Layer, time: float) -> None:
        if layer.type == "image":
            self._draw_image_layer(canvas, layer)
        elif layer.type in {"text", "text3d"}:
            self._draw_text_layer(canvas, layer)
        elif layer.type == "shape":
            self._draw_shape_layer(canvas, layer)
        elif layer.type == "particle":
            self._draw_particle_placeholder(canvas, layer)
        elif layer.type in {"camera", "light", "audio", "video"}:
            return
        elif layer.type in {"diagram_node", "connector_line", "measurement"}:
            self._draw_diagram_layer(canvas, layer)

    def _apply_effects(self, image: Image.Image, effects: Iterable[dict]) -> Image.Image:
        out = image
        for effect in effects:
            effect_type = effect.get("type")
            if effect_type == "blur":
                out = out.filter(ImageFilter.GaussianBlur(float(effect.get("amount", 2))))
            elif effect_type == "glow":
                glow = out.filter(ImageFilter.GaussianBlur(float(effect.get("amount", 6))))
                out = Image.alpha_composite(glow, out)
        return out

    def _draw_image_layer(self, canvas: Image.Image, layer: Layer) -> None:
        asset_path = layer.properties.get("path") or layer.properties.get("asset_path")
        if not asset_path:
            return
        path = self.context.resolve_asset(str(asset_path))
        if not path.exists():
            return
        image = Image.open(path).convert("RGBA")
        image = self._apply_effects(image, layer.effects)
        w = max(1, int(image.width * layer.transform.scale_x))
        h = max(1, int(image.height * layer.transform.scale_y))
        image = image.resize((w, h), Image.Resampling.LANCZOS)
        if layer.transform.rotation_z:
            image = image.rotate(layer.transform.rotation_z, expand=True, resample=Image.Resampling.BICUBIC)
        if layer.transform.opacity < 1:
            image.putalpha(image.getchannel("A").point(lambda p: int(p * layer.transform.opacity)))
        canvas.alpha_composite(image, (int(layer.transform.x), int(layer.transform.y)))

    def _draw_text_layer(self, canvas: Image.Image, layer: Layer) -> None:
        text = str(layer.properties.get("text", layer.name))
        image = render_text_layer(canvas.size, text, layer.transform.x, layer.transform.y, layer.properties)
        if layer.transform.opacity < 1:
            image.putalpha(image.getchannel("A").point(lambda p: int(p * layer.transform.opacity)))
        canvas.alpha_composite(image)

    def _draw_shape_layer(self, canvas: Image.Image, layer: Layer) -> None:
        shape = layer.properties.get("shape", "rectangle")
        fill = layer.properties.get("fill", "#00E5FF")
        outline = layer.properties.get("outline")
        width = float(layer.properties.get("width", 200)) * layer.transform.scale_x
        height = float(layer.properties.get("height", 100)) * layer.transform.scale_y
        draw = ImageDraw.Draw(canvas)
        box = (layer.transform.x, layer.transform.y, layer.transform.x + width, layer.transform.y + height)
        if shape == "ellipse":
            draw.ellipse(box, fill=fill, outline=outline)
        else:
            radius = int(layer.properties.get("radius", 0))
            if radius:
                draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline)
            else:
                draw.rectangle(box, fill=fill, outline=outline)

    def _draw_particle_placeholder(self, canvas: Image.Image, layer: Layer) -> None:
        draw = ImageDraw.Draw(canvas)
        colors = layer.properties.get("colors", ["#00E5FF", "#BC13FE"])
        density = int(layer.properties.get("density", 30))
        for i in range(min(density, 160)):
            x = (i * 97) % canvas.width
            y = (i * 53) % canvas.height
            color = colors[i % len(colors)]
            draw.ellipse((x, y, x + 3, y + 3), fill=color)

    def _draw_diagram_layer(self, canvas: Image.Image, layer: Layer) -> None:
        draw = ImageDraw.Draw(canvas)
        color = layer.properties.get("color", "#00E5FF")
        if layer.type == "connector_line":
            points = layer.properties.get("points", [[0, 0], [100, 100]])
            draw.line([tuple(p) for p in points], fill=color, width=int(layer.properties.get("stroke_width", 3)))
        elif layer.type == "measurement":
            points = layer.properties.get("points", [[0, 0], [100, 0]])
            draw.line([tuple(p) for p in points], fill=color, width=2)
            draw.text(tuple(points[-1]), str(layer.properties.get("label", "measurement")), fill=color)
        else:
            x, y = layer.transform.x, layer.transform.y
            w = layer.properties.get("width", 160)
            h = layer.properties.get("height", 80)
            draw.rounded_rectangle((x, y, x + w, y + h), radius=12, outline=color, width=3)
            draw.text((x + 12, y + 24), str(layer.properties.get("label", layer.name)), fill=color)
