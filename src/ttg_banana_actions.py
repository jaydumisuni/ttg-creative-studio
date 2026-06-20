#!/usr/bin/env python3
"""Initial Banana Level actions.

These actions must be deterministic and useful without AI. AI can later choose or
combine them, but the tool should already do damage on its own.
"""

from __future__ import annotations

from ttg_project_schema import TTGProject
from ttg_preset_actions import PresetActions


class BananaActions:
    def __init__(self) -> None:
        self.presets = PresetActions()

    def make_it_pop(self, project: TTGProject) -> None:
        project.export.setdefault("banana", {})["last_workflow"] = "make_it_pop"
        project.export["banana"]["promise"] = "Polished glow, contrast and premium text depth."
        for layer in project.layers:
            if layer.type in {"text", "text3d"}:
                layer.properties.update({
                    "glow": True,
                    "glow_color": "#00E5FF",
                    "glow_blur": max(int(layer.properties.get("glow_blur", 8)), 12),
                    "stroke_width": max(int(layer.properties.get("stroke_width", 1)), 3),
                    "stroke_fill": layer.properties.get("stroke_fill", "#120026"),
                    "shadow": True,
                    "shadow_blur": max(int(layer.properties.get("shadow_blur", 6)), 10),
                    "gradient": True,
                    "gradient_start": layer.properties.get("gradient_start", "#BC13FE"),
                    "gradient_end": layer.properties.get("gradient_end", "#00E5FF"),
                })
                if layer.type == "text":
                    layer.type = "text3d"
            elif layer.type in {"shape", "image"}:
                layer.properties.setdefault("shadow", True)
                layer.properties.setdefault("glow", True)
                layer.properties.setdefault("opacity", 0.96)

    def brand_everything(self, project: TTGProject, primary: str = "#00E5FF", accent: str = "#BC13FE") -> None:
        project.export.setdefault("banana", {})["last_workflow"] = "brand_everything"
        project.export["banana"]["primary"] = primary
        project.export["banana"]["accent"] = accent
        for layer in project.layers:
            if layer.type in {"text", "text3d"}:
                layer.properties.setdefault("gradient", True)
                layer.properties["gradient_start"] = accent
                layer.properties["gradient_end"] = primary
                layer.properties.setdefault("glow", True)
                layer.properties["glow_color"] = primary
            elif layer.type == "shape":
                layer.properties["fill"] = layer.properties.get("fill", "#07132F80")
                layer.properties["stroke_fill"] = primary
