#!/usr/bin/env python3
"""Render planning for TTG Creative Studio.

A render plan turns an editable project into ordered render tasks. The first
backend is the simple 2D renderer; later backends can include Three.js,
Blender, Remotion, or dedicated GPU render services.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ttg_project_schema import TTGProject


@dataclass
class RenderTask:
    id: str
    backend: str
    layer_ids: list[str]
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderPlan:
    project_name: str
    canvas: dict[str, Any]
    tasks: list[RenderTask]
    output: dict[str, Any]


class RenderPlanner:
    def create_plan(self, project: TTGProject) -> RenderPlan:
        two_d_layers: list[str] = []
        three_d_layers: list[str] = []
        audio_layers: list[str] = []
        for layer in project.layers:
            if layer.type in {"text3d", "camera", "light"}:
                three_d_layers.append(layer.id)
            elif layer.type == "audio":
                audio_layers.append(layer.id)
            else:
                two_d_layers.append(layer.id)
        tasks: list[RenderTask] = []
        if three_d_layers:
            tasks.append(RenderTask("scene3d", "threejs_or_blender", three_d_layers, {"status": "planned"}))
        if two_d_layers:
            tasks.append(RenderTask("composite2d", "pillow", two_d_layers, {"status": "available"}))
        if audio_layers or project.audio_markers:
            tasks.append(RenderTask("audio", "ffmpeg", audio_layers, {"markers": project.audio_markers, "status": "planned"}))
        return RenderPlan(
            project_name=project.name,
            canvas={
                "width": project.canvas.width,
                "height": project.canvas.height,
                "fps": project.canvas.fps,
                "duration": project.canvas.duration,
            },
            tasks=tasks,
            output=project.export,
        )
