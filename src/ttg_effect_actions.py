#!/usr/bin/env python3
"""Advanced visual effect actions for TTG Creative Studio."""

from __future__ import annotations

from ttg_project_schema import TTGProject


class EffectActions:
    def _layer(self, project: TTGProject, layer_id: str):
        for layer in project.layers:
            if layer.id == layer_id:
                return layer
        raise KeyError(layer_id)

    def apply_neon_glow(self, project: TTGProject, layer_id: str, color: str = "#00E5FF", blur: float = 12, alpha: float = 0.85) -> None:
        layer = self._layer(project, layer_id)
        layer.properties["glow"] = True
        layer.properties["glow_color"] = color
        layer.properties["glow_blur"] = blur
        layer.properties["glow_alpha"] = alpha

    def apply_stroke_shadow(self, project: TTGProject, layer_id: str, stroke: str = "#00111F", shadow: str = "#000000AA") -> None:
        layer = self._layer(project, layer_id)
        layer.properties["stroke_width"] = max(1, int(layer.properties.get("stroke_width", 1)))
        layer.properties["stroke_fill"] = stroke
        layer.properties["shadow"] = True
        layer.properties["shadow_fill"] = shadow
        layer.properties["shadow_blur"] = 8

    def apply_bevel_extrude(self, project: TTGProject, layer_id: str, depth: int = 18) -> None:
        layer = self._layer(project, layer_id)
        layer.type = "text3d" if layer.type == "text" else layer.type
        layer.properties["extrude_px"] = depth
        layer.properties["extrude_color"] = "#210040"
        layer.properties["bevel"] = True
        layer.properties["material"] = "neon_chrome"

    def apply_reflection(self, project: TTGProject, layer_id: str, strength: float = 0.35) -> None:
        layer = self._layer(project, layer_id)
        layer.properties["reflection"] = True
        layer.properties["reflection_strength"] = max(0.0, min(1.0, strength))
        layer.properties["reflection_blur"] = 10

    def apply_gradient(self, project: TTGProject, layer_id: str, start: str = "#BC13FE", end: str = "#00E5FF") -> None:
        layer = self._layer(project, layer_id)
        layer.properties["gradient"] = True
        layer.properties["gradient_start"] = start
        layer.properties["gradient_end"] = end
        layer.properties.setdefault("color", start)

    def apply_premium_text_stack(self, project: TTGProject, layer_id: str) -> None:
        self.apply_gradient(project, layer_id)
        self.apply_stroke_shadow(project, layer_id)
        self.apply_neon_glow(project, layer_id)
        self.apply_bevel_extrude(project, layer_id, 22)
        self.apply_reflection(project, layer_id, 0.28)
