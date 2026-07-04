#!/usr/bin/env python3
"""Editable property engine for TTG Creative Studio.

UI last: this engine applies layer/property/effect edits before a polished
properties panel is built on top.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ttg_canvas_tools import get_layer
from ttg_project_schema import Layer, TTGProject


@dataclass(frozen=True)
class PropertyEdit:
    layer_id: str
    path: str
    value: Any


TRANSFORM_FIELDS = {
    "x", "y", "z", "scale_x", "scale_y", "scale_z",
    "rotation_x", "rotation_y", "rotation_z", "opacity",
}


def _coerce_number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a numeric property value")
    return float(value)


def set_layer_property(project: TTGProject, layer_id: str, path: str, value: Any) -> Layer:
    layer = get_layer(project, layer_id)
    if layer.locked:
        raise ValueError(f"Layer is locked: {layer_id}")

    if path == "name":
        layer.name = str(value)
    elif path == "visible":
        layer.visible = bool(value)
    elif path == "locked":
        layer.locked = bool(value)
    elif path.startswith("transform."):
        field = path.split(".", 1)[1]
        if field not in TRANSFORM_FIELDS:
            raise KeyError(path)
        setattr(layer.transform, field, _coerce_number(value))
    elif path.startswith("properties."):
        key = path.split(".", 1)[1]
        layer.properties[key] = value
    elif path.startswith("effect."):
        _, effect_id, key = path.split(".", 2)
        effect = ensure_effect(layer, effect_id)
        effect[key] = value
    else:
        raise KeyError(path)
    return layer


def ensure_effect(layer: Layer, effect_id: str) -> dict[str, Any]:
    for effect in layer.effects:
        if effect.get("id") == effect_id:
            return effect
    effect = {"id": effect_id, "enabled": True}
    layer.effects.append(effect)
    return effect


def apply_property_edits(project: TTGProject, edits: list[PropertyEdit]) -> TTGProject:
    for edit in edits:
        set_layer_property(project, edit.layer_id, edit.path, edit.value)
    return project


def describe_editable_properties(layer: Layer) -> dict[str, Any]:
    return {
        "layer": {
            "id": layer.id,
            "name": layer.name,
            "type": layer.type,
            "visible": layer.visible,
            "locked": layer.locked,
        },
        "transform": {
            "x": layer.transform.x,
            "y": layer.transform.y,
            "z": layer.transform.z,
            "scale_x": layer.transform.scale_x,
            "scale_y": layer.transform.scale_y,
            "rotation_z": layer.transform.rotation_z,
            "opacity": layer.transform.opacity,
        },
        "properties": dict(layer.properties),
        "effects": list(layer.effects),
    }
