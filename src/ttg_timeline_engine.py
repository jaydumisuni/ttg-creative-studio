#!/usr/bin/env python3
"""Timeline helpers for TTG Creative Studio."""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from ttg_project_schema import Easing, Keyframe, Layer


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _cubic(y1: float, y2: float, u: float) -> float:
    """Normalized Bernstein cubic with endpoints (0, 1)."""
    v = 1.0 - u
    return 3.0 * v * v * u * y1 + 3.0 * v * u * u * y2 + u * u * u


def _cubic_ease(t: float, handles: object) -> float:
    """Time-parametric easing: invert the X cubic before evaluating the Y cubic.

    The design is TTG-native and uses only an editable four-number project field.
    The numerical regression comes from EffectCraft's public AE velocity fixtures
    (storytold/effectcraft, crates/keyframe/src/tests.rs). No donor runtime or
    UI code is imported.
    """
    if (not isinstance(handles, (list, tuple)) or len(handles) != 4
            or any(not isinstance(v, (int, float)) or isinstance(v, bool)
                   or not math.isfinite(v) for v in handles)):
        raise ValueError("Cubic easing requires four finite numeric handles")
    x1, y1, x2, y2 = (float(v) for v in handles)
    if not (0.0 <= x1 <= 1.0 and 0.0 <= x2 <= 1.0):
        raise ValueError("Cubic easing time handles must be in [0, 1]")
    if t <= 0.0:
        return 0.0
    if t >= 1.0:
        return 1.0
    if x1 == 1.0 and x2 == 0.0:
        # x = 0.5 + 4*(u - 0.5)^3; ordinary bisection loses precision at
        # the stationary midpoint, where a tiny x error produces a large u error.
        displacement = (t - 0.5) / 4.0
        u = 0.5 + math.copysign(abs(displacement) ** (1.0 / 3.0), displacement)
        return _cubic(y1, y2, u)
    # X is monotone for x1,x2 in [0,1], including crossing handle order.
    # Bisection handles the 100%-influence flat derivative without an unstable
    # Newton step, while the Y handles can intentionally overshoot [0,1].
    low, high = 0.0, 1.0
    for _ in range(60):
        middle = (low + high) * 0.5
        if _cubic(x1, x2, middle) < t:
            low = middle
        else:
            high = middle
    result = _cubic(y1, y2, (low + high) * 0.5)
    if not math.isfinite(result):
        raise ValueError("Cubic easing output exceeds finite range")
    return result


def ease_value(t: float, easing: Easing) -> float:
    t = clamp(t, 0.0, 1.0)
    if isinstance(easing, dict):
        if set(easing) != {"type", "handles"} or easing["type"] != "cubic_bezier":
            raise ValueError("Unsupported TTG easing curve contract")
        return _cubic_ease(t, easing["handles"])
    if not isinstance(easing, str):
        raise ValueError("Easing must be a string or a cubic_bezier object")
    if easing == "hold":
        return 0.0 if t < 1.0 else 1.0
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
