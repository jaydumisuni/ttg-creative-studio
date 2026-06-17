#!/usr/bin/env python3
"""Timeline action helpers for TTG Creative Studio."""

from __future__ import annotations

from ttg_project_schema import Keyframe, TTGProject


class TimelineActions:
    def add_position_hold(self, project: TTGProject, layer_id: str, start_time: float = 0.0, end_time: float | None = None) -> None:
        layer = self._layer(project, layer_id)
        if end_time is None:
            end_time = project.canvas.duration
        layer.keyframes["position"] = [
            Keyframe(start_time, [layer.transform.x, layer.transform.y, layer.transform.z], "ease_in_out"),
            Keyframe(end_time, [layer.transform.x, layer.transform.y, layer.transform.z], "ease_in_out"),
        ]

    def add_fly_in_left(self, project: TTGProject, layer_id: str, start_time: float = 0.0, end_time: float = 1.0) -> None:
        layer = self._layer(project, layer_id)
        target = [layer.transform.x, layer.transform.y, layer.transform.z]
        start = [-project.canvas.width, layer.transform.y, layer.transform.z]
        layer.keyframes["position"] = [Keyframe(start_time, start, "ease_out_back"), Keyframe(end_time, target, "ease_out_back")]
        layer.keyframes["opacity"] = [Keyframe(start_time, 0, "linear"), Keyframe(end_time, 1, "ease_in_out")]

    def add_fade_in(self, project: TTGProject, layer_id: str, start_time: float = 0.0, end_time: float = 1.0) -> None:
        layer = self._layer(project, layer_id)
        layer.keyframes["opacity"] = [Keyframe(start_time, 0, "linear"), Keyframe(end_time, 1, "ease_in_out")]

    def add_pulse(self, project: TTGProject, layer_id: str, start_time: float = 0.0, end_time: float | None = None) -> None:
        layer = self._layer(project, layer_id)
        if end_time is None:
            end_time = project.canvas.duration
        mid = (start_time + end_time) / 2
        layer.keyframes["scale"] = [
            Keyframe(start_time, [1.0, 1.0, 1.0], "ease_in_out"),
            Keyframe(mid, [1.08, 1.08, 1.0], "ease_in_out"),
            Keyframe(end_time, [1.0, 1.0, 1.0], "ease_in_out"),
        ]

    def clear_animation(self, project: TTGProject, layer_id: str) -> None:
        self._layer(project, layer_id).keyframes.clear()

    def _layer(self, project: TTGProject, layer_id: str):
        for layer in project.layers:
            if layer.id == layer_id:
                return layer
        raise KeyError(layer_id)
