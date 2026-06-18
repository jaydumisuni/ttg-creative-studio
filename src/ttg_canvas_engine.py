#!/usr/bin/env python3
"""2D/2.5D canvas renderer for TTG Creative Studio."""

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
            direct = self.asset_root / asset_path
            if direct.exists():
                return direct
        direct = self.project_root / asset_path
        if direct.exists():
            return direct
        resources = self.project_root / "resources" / asset_path
        if resources.exists():
            return resources
        return direct


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

    def _draw_reflection(self, canvas: Image.Image, image: Image.Image, x: int, y: int, strength: float = 0.3) -> None:
        reflection = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        reflection = reflection.filter(ImageFilter.GaussianBlur(8))
        alpha = reflection.getchannel("A")
        height = reflection.height
        gradient = Image.new("L", reflection.size, 0)
        gd = ImageDraw.Draw(gradient)
        for row in range(height):
            opacity = int(255 * strength * max(0, 1 - row / max(1, height)))
            gd.line((0, row, reflection.width, row), fill=opacity)
        reflection.putalpha(Image.composite(alpha, gradient, gradient))
        canvas.alpha_composite(reflection, (x, y + image.height + 8))

    def _draw_image_layer(self, canvas: Image.Image, layer: Layer) -> None:
        asset_path = layer.properties.get("path") or layer.properties.get("asset_path") or layer.properties.get("asset")
        if asset_path == "ttg_ghost_original":
            asset_path = "resources/logo.png"
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
        if layer.properties.get("glow"):
            glow = image.filter(ImageFilter.GaussianBlur(float(layer.properties.get("glow_blur", 12))))
            canvas.alpha_composite(glow, (int(layer.transform.x), int(layer.transform.y)))
        if layer.transform.rotation_z:
            image = image.rotate(layer.transform.rotation_z, expand=True, resample=Image.Resampling.BICUBIC)
        if layer.transform.opacity < 1:
            image.putalpha(image.getchannel("A").point(lambda p: int(p * layer.transform.opacity)))
        x, y = int(layer.transform.x), int(layer.transform.y)
        canvas.alpha_composite(image, (x, y))
        if layer.properties.get("reflection"):
            self._draw_reflection(canvas, image, x, y, float(layer.properties.get("reflection_strength", 0.25)))

    def _draw_text_layer(self, canvas: Image.Image, layer: Layer) -> None:
        text = str(layer.properties.get("text", layer.name))
        depth = int(layer.properties.get("extrude_px", 0 if layer.type == "text" else 12))
        if depth:
            extrude_props = dict(layer.properties)
            extrude_props["color"] = layer.properties.get("extrude_color", "#1A0038")
            extrude_props["glow"] = False
            extrude_props["shadow"] = False
            for offset in range(depth, 0, -3):
                canvas.alpha_composite(render_text_layer(canvas.size, text, layer.transform.x + offset, layer.transform.y + offset, extrude_props))
        image = render_text_layer(canvas.size, text, layer.transform.x, layer.transform.y, layer.properties)
        if layer.transform.opacity < 1:
            image.putalpha(image.getchannel("A").point(lambda p: int(p * layer.transform.opacity)))
        canvas.alpha_composite(image)
        if layer.properties.get("reflection"):
            bbox = image.getbbox()
            if bbox:
                crop = image.crop(bbox)
                self._draw_reflection(canvas, crop, bbox[0], bbox[1], float(layer.properties.get("reflection_strength", 0.25)))

    def _draw_shape_layer(self, canvas: Image.Image, layer: Layer) -> None:
        shape = layer.properties.get("shape", "rectangle")
        fill = layer.properties.get("fill", "#00E5FF")
        outline = layer.properties.get("outline")
        width = float(layer.properties.get("width", 200)) * layer.transform.scale_x
        height = float(layer.properties.get("height", 100)) * layer.transform.scale_y
        x, y = layer.transform.x, layer.transform.y
        box = (x, y, x + width, y + height)
        shape_img = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(shape_img)
        radius = int(layer.properties.get("radius", 0))
        if shape == "ellipse":
            draw.ellipse(box, fill=fill, outline=outline, width=3 if outline else 1)
        elif radius:
            draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=3 if outline else 1)
        else:
            draw.rectangle(box, fill=fill, outline=outline, width=3 if outline else 1)
        if layer.properties.get("glow") and outline:
            glow = shape_img.filter(ImageFilter.GaussianBlur(float(layer.properties.get("glow_blur", 10))))
            canvas.alpha_composite(glow)
        canvas.alpha_composite(shape_img)

    def _draw_particle_placeholder(self, canvas: Image.Image, layer: Layer) -> None:
        draw = ImageDraw.Draw(canvas)
        colors = layer.properties.get("colors", ["#00E5FF", "#BC13FE"])
        density = int(layer.properties.get("density", 30))
        for i in range(min(density, 520)):
            x = (i * 97) % canvas.width
            y = (i * 53) % canvas.height
            color = colors[i % len(colors)]
            size = 2 + (i % 4)
            draw.ellipse((x, y, x + size, y + size), fill=color)

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
