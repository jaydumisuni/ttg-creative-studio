#!/usr/bin/env python3
"""Layer property editing helpers for TTG Creative Studio."""

from __future__ import annotations

from typing import Any

from ttg_project_schema import Layer, TTGProject


class PropertyActions:
    def get_layer(self, project: TTGProject, layer_id: str) -> Layer:
        for layer in project.layers:
            if layer.id == layer_id:
                return layer
        raise KeyError(layer_id)

    def rename_layer(self, project: TTGProject, layer_id: str, name: str) -> None:
        self.get_layer(project, layer_id).name = name.strip() or "Layer"

    def set_text(self, project: TTGProject, layer_id: str, text: str) -> None:
        layer = self.get_layer(project, layer_id)
        layer.properties["text"] = text
        if layer.type in {"text", "text3d"}:
            layer.name = text[:32] or layer.name

    def set_position(self, project: TTGProject, layer_id: str, x: float, y: float) -> None:
        layer = self.get_layer(project, layer_id)
        layer.transform.x = float(x)
        layer.transform.y = float(y)

    def set_scale(self, project: TTGProject, layer_id: str, scale_x: float, scale_y: float | None = None) -> None:
        layer = self.get_layer(project, layer_id)
        layer.transform.scale_x = max(0.01, float(scale_x))
        layer.transform.scale_y = max(0.01, float(scale_y if scale_y is not None else scale_x))

    def set_rotation(self, project: TTGProject, layer_id: str, rotation_z: float) -> None:
        self.get_layer(project, layer_id).transform.rotation_z = float(rotation_z)

    def set_opacity(self, project: TTGProject, layer_id: str, opacity: float) -> None:
        self.get_layer(project, layer_id).transform.opacity = max(0.0, min(1.0, float(opacity)))

    def set_color(self, project: TTGProject, layer_id: str, color: str) -> None:
        self.get_layer(project, layer_id).properties["color"] = color

    def set_fill(self, project: TTGProject, layer_id: str, fill: str) -> None:
        self.get_layer(project, layer_id).properties["fill"] = fill

    def set_size(self, project: TTGProject, layer_id: str, size: int) -> None:
        self.get_layer(project, layer_id).properties["size"] = max(1, int(size))

    def set_property(self, project: TTGProject, layer_id: str, key: str, value: Any) -> None:
        self.get_layer(project, layer_id).properties[key] = value
