#!/usr/bin/env python3
"""Canvas hit-testing and selection helpers for TTG Creative Studio."""

from __future__ import annotations

from dataclasses import dataclass

from ttg_project_schema import Layer, TTGProject


@dataclass
class LayerBounds:
    layer_id: str
    x: float
    y: float
    width: float
    height: float

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px <= self.x + self.width and self.y <= py <= self.y + self.height


class CanvasSelection:
    def layer_bounds(self, layer: Layer) -> LayerBounds:
        width = float(layer.properties.get("width", 220)) * layer.transform.scale_x
        height = float(layer.properties.get("height", 90)) * layer.transform.scale_y
        if layer.type in {"text", "text3d"}:
            text = str(layer.properties.get("text", layer.name))
            size = float(layer.properties.get("size", 72))
            width = max(40, len(text) * size * 0.55) * layer.transform.scale_x
            height = max(30, size * 1.25) * layer.transform.scale_y
        return LayerBounds(layer.id, layer.transform.x, layer.transform.y, width, height)

    def hit_test(self, project: TTGProject, x: float, y: float) -> str | None:
        # Check topmost first. Later layers render on top.
        for layer in reversed(project.layers):
            if not layer.visible or layer.locked:
                continue
            if self.layer_bounds(layer).contains(x, y):
                return layer.id
        return None

    def all_bounds(self, project: TTGProject) -> list[LayerBounds]:
        return [self.layer_bounds(layer) for layer in project.layers if layer.visible]
