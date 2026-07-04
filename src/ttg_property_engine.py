#!/usr/bin/env python3
"""Editable property and timeline engine for TTG Creative Studio.

UI last: this engine applies layer/property/effect/time edits before polished
panels are built on top.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ttg_canvas_tools import get_layer
from ttg_project_schema import Keyframe, Layer, TTGProject


@dataclass(frozen=True)
class PropertyEdit:
    layer_id: str
    path: str
    value: Any


@dataclass(frozen=True)
class TimelineClip:
    layer_id: str
    start: float
    end: float


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
    if layer.locked and path != "locked":
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


def set_layer_time(project: TTGProject, layer_id: str, start: float, end: float) -> None:
    if end <= start:
        raise ValueError("Layer end time must be after start time")
    layer = get_layer(project, layer_id)
    layer.properties["start_time"] = float(start)
    layer.properties["end_time"] = float(end)
    project.canvas.duration = max(float(project.canvas.duration), float(end))


def add_layer_keyframe(project: TTGProject, layer_id: str, prop: str, time: float, value: Any, easing: str = "ease_in_out") -> None:
    layer = get_layer(project, layer_id)
    frames = layer.keyframes.setdefault(prop, [])
    frames.append(Keyframe(float(time), value, easing))
    frames.sort(key=lambda frame: frame.time)
    project.canvas.duration = max(float(project.canvas.duration), float(time))


def list_timeline_clips(project: TTGProject) -> list[TimelineClip]:
    clips: list[TimelineClip] = []
    for layer in project.layers:
        start = float(layer.properties.get("start_time", 0.0))
        end = float(layer.properties.get("end_time", project.canvas.duration))
        clips.append(TimelineClip(layer.id, start, end))
    return sorted(clips, key=lambda clip: (clip.start, clip.end, clip.layer_id))


def evaluate_keyframes(project: TTGProject, layer_id: str, prop: str, time: float) -> Any:
    layer = get_layer(project, layer_id)
    frames = sorted(layer.keyframes.get(prop, []), key=lambda frame: frame.time)
    if not frames:
        return None
    if time <= frames[0].time:
        return frames[0].value
    if time >= frames[-1].time:
        return frames[-1].value
    previous = frames[0]
    for current in frames[1:]:
        if time <= current.time:
            if not isinstance(previous.value, (int, float)) or not isinstance(current.value, (int, float)):
                return previous.value
            span = current.time - previous.time
            if span <= 0:
                return current.value
            ratio = (time - previous.time) / span
            return previous.value + (current.value - previous.value) * ratio
        previous = current
    return frames[-1].value
