#!/usr/bin/env python3
"""Timeline helpers for TTG Creative Studio."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ttg_project_schema import Keyframe, Layer


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def ease_value(t: float, easing: str) -> float:
    t = clamp(t, 0.0, 1.0)
    if easing == "linear":
        return t
    if easing == "ease_in":
        return t * t
    if easing == "ease_out":
        return 1 - ((1 - t) * (1 - t))
    if easing == "ease_out_back":
        c1 = 1.70158
        c3 = c1 + 1
        return 1 + c3 * ((t - 1) ** 3) + c1 * ((t - 1) ** 2)
    return t * t * (3 - 2 * t)


def lerp(a: Any, b: Any, t: float) -> Any:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return a + (b - a) * t
    if isinstance(a, list) and isinstance(b, list):
        return [lerp(x, y, t) for x, y in zip(a, b)]
    return b if t >= 1 else a


class TimelineEngine:
    def value_at(self, frames: list[Keyframe], time: float) -> Any:
        if not frames:
            return None
        frames = sorted(frames, key=lambda item: item.time)
        if time <= frames[0].time:
            return frames[0].value
        if time >= frames[-1].time:
            return frames[-1].value
        for left, right in zip(frames, frames[1:]):
            if left.time <= time <= right.time:
                span = max(0.0001, right.time - left.time)
                local = (time - left.time) / span
                return lerp(left.value, right.value, ease_value(local, right.easing))
        return frames[-1].value

    def apply_to_layer(self, layer: Layer, time: float) -> Layer:
        layer = deepcopy(layer)
        for prop, frames in layer.keyframes.items():
            value = self.value_at(frames, time)
            if value is None:
                continue
            if prop == "position":
                layer.transform.x = float(value[0])
                layer.transform.y = float(value[1])
                if len(value) > 2:
                    layer.transform.z = float(value[2])
            elif prop == "scale":
                if isinstance(value, (int, float)):
                    layer.transform.scale_x = layer.transform.scale_y = layer.transform.scale_z = float(value)
                else:
                    layer.transform.scale_x = float(value[0])
                    layer.transform.scale_y = float(value[1])
                    if len(value) > 2:
                        layer.transform.scale_z = float(value[2])
            elif prop == "rotation":
                if isinstance(value, (int, float)):
                    layer.transform.rotation_z = float(value)
                else:
                    layer.transform.rotation_x = float(value[0])
                    layer.transform.rotation_y = float(value[1])
                    if len(value) > 2:
                        layer.transform.rotation_z = float(value[2])
            elif prop == "opacity":
                layer.transform.opacity = clamp(float(value), 0.0, 1.0)
            else:
                layer.properties[prop] = value
        return layer
