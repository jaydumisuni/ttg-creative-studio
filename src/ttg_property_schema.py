#!/usr/bin/env python3
"""Editable property schema for TTG Creative Studio layers.

The Properties panel should eventually build editors from this schema instead of
hard-coding random fields. This keeps normal properties and Advanced Mode preset
properties aligned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PropertySpec:
    key: str
    label: str
    editor: str
    default: Any
    applies_to: tuple[str, ...]
    min_value: float | None = None
    max_value: float | None = None


COMMON = ("image", "text", "text3d", "shape", "svg", "video", "group")
TEXT = ("text", "text3d")
VISUAL = ("image", "text", "text3d", "shape", "svg")


PROPERTY_SPECS = [
    PropertySpec("name", "Layer name", "text", "", COMMON),
    PropertySpec("x", "X", "number", 0, COMMON),
    PropertySpec("y", "Y", "number", 0, COMMON),
    PropertySpec("scale", "Scale", "number", 1.0, COMMON, 0.01, 20.0),
    PropertySpec("rotation", "Rotation", "number", 0.0, COMMON, -360.0, 360.0),
    PropertySpec("opacity", "Opacity", "number", 1.0, COMMON, 0.0, 1.0),
    PropertySpec("text", "Text", "multiline", "", TEXT),
    PropertySpec("size", "Text size", "number", 72, TEXT, 1, 600),
    PropertySpec("color", "Text color", "color", "#F7FAFF", TEXT),
    PropertySpec("fill", "Fill", "color", "#16224d", ("shape",)),
    PropertySpec("stroke_width", "Stroke width", "number", 0, VISUAL, 0, 40),
    PropertySpec("stroke_fill", "Stroke color", "color", "#000000", VISUAL),
    PropertySpec("shadow", "Shadow", "bool", False, VISUAL),
    PropertySpec("shadow_blur", "Shadow blur", "number", 0, VISUAL, 0, 80),
    PropertySpec("glow", "Glow", "bool", False, VISUAL),
    PropertySpec("glow_color", "Glow color", "color", "#00E5FF", VISUAL),
    PropertySpec("glow_blur", "Glow blur", "number", 0, VISUAL, 0, 100),
    PropertySpec("gradient", "Gradient", "bool", False, TEXT),
    PropertySpec("gradient_start", "Gradient start", "color", "#BC13FE", TEXT),
    PropertySpec("gradient_end", "Gradient end", "color", "#00E5FF", TEXT),
    PropertySpec("extrude_px", "Extrude depth", "number", 0, ("text3d",), 0, 120),
    PropertySpec("extrude_color", "Extrude color", "color", "#170033", ("text3d",)),
    PropertySpec("reflection", "Reflection", "bool", False, VISUAL),
]


def specs_for_layer_type(layer_type: str) -> list[PropertySpec]:
    return [spec for spec in PROPERTY_SPECS if layer_type in spec.applies_to]


def spec_by_key(key: str) -> PropertySpec:
    for spec in PROPERTY_SPECS:
        if spec.key == key:
            return spec
    raise KeyError(key)


def editable_keys_for_layer_type(layer_type: str) -> list[str]:
    return [spec.key for spec in specs_for_layer_type(layer_type)]
