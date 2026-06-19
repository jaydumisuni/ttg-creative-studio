#!/usr/bin/env python3
"""Apply Advanced Mode presets to TTG projects and layers."""

from __future__ import annotations

from ttg_advanced_presets import find_preset
from ttg_project_schema import TTGProject


class PresetActions:
    def _layer(self, project: TTGProject, layer_id: str):
        for layer in project.layers:
            if layer.id == layer_id:
                return layer
        raise KeyError(layer_id)

    def apply_to_layer(self, project: TTGProject, layer_id: str, preset_id: str) -> None:
        preset = find_preset(preset_id)
        layer = self._layer(project, layer_id)
        props = dict(preset.properties)
        layer.properties.update(props)
        if "extrude_px" in props and layer.type == "text":
            layer.type = "text3d"
        layer.properties["advanced_preset"] = preset_id
        layer.properties["advanced_preset_name"] = preset.name

    def apply_scene_preset(self, project: TTGProject, preset_id: str) -> None:
        preset = find_preset(preset_id)
        project.metadata["scene_preset"] = preset_id
        project.metadata["scene_preset_name"] = preset.name
        project.metadata.setdefault("advanced_scene", {}).update(preset.properties)

    def apply_motion_preset(self, project: TTGProject, preset_id: str) -> None:
        preset = find_preset(preset_id)
        project.metadata["motion_preset"] = preset_id
        project.metadata["motion_preset_name"] = preset.name
        project.metadata.setdefault("advanced_motion", {}).update(preset.properties)

    def apply_export_preset(self, project: TTGProject, preset_id: str) -> None:
        preset = find_preset(preset_id)
        project.metadata["export_preset"] = preset_id
        project.metadata["export_preset_name"] = preset.name
        for key, value in preset.properties.items():
            if key in {"width", "height", "fps"}:
                setattr(project.canvas, key, value)
            else:
                project.metadata.setdefault("export", {})[key] = value
