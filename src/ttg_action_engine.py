#!/usr/bin/env python3
"""Action engine for manual UI commands and future Hunter control."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ttg_project_schema import Layer, TTGProject, Transform, new_id


class ActionEngine:
    def new_project(self, name: str = "Untitled TTG Project", project_type: str = "image") -> TTGProject:
        return TTGProject(name=name, project_type=project_type)  # type: ignore[arg-type]

    def add_text(self, project: TTGProject, text: str, x: float = 100, y: float = 100, name: str | None = None) -> Layer:
        layer = Layer(
            id=new_id("text"),
            type="text",
            name=name or text[:32] or "Text",
            transform=Transform(x=x, y=y),
            properties={"text": text, "size": 72, "color": "#F7FAFF"},
        )
        project.layers.append(layer)
        return layer

    def add_image(self, project: TTGProject, path: str, x: float = 0, y: float = 0, name: str | None = None) -> Layer:
        layer = Layer(
            id=new_id("image"),
            type="image",
            name=name or Path(path).stem,
            transform=Transform(x=x, y=y),
            properties={"path": path},
        )
        project.layers.append(layer)
        return layer

    def add_shape(self, project: TTGProject, shape: str = "rectangle", x: float = 100, y: float = 100) -> Layer:
        layer = Layer(
            id=new_id("shape"),
            type="shape",
            name=f"{shape.title()} Shape",
            transform=Transform(x=x, y=y),
            properties={"shape": shape, "width": 240, "height": 120, "fill": "#00E5FF"},
        )
        project.layers.append(layer)
        return layer

    def add_keyframe(self, project: TTGProject, layer_id: str, prop: str, time: float, value: Any, easing: str = "ease_in_out") -> None:
        from ttg_project_schema import Keyframe

        layer = self.get_layer(project, layer_id)
        layer.keyframes.setdefault(prop, []).append(Keyframe(time=time, value=value, easing=easing))
        layer.keyframes[prop].sort(key=lambda item: item.time)

    def get_layer(self, project: TTGProject, layer_id: str) -> Layer:
        for layer in project.layers:
            if layer.id == layer_id:
                return layer
        raise KeyError(f"Layer not found: {layer_id}")

    def move_layer(self, project: TTGProject, layer_id: str, x: float, y: float) -> None:
        layer = self.get_layer(project, layer_id)
        layer.transform.x = x
        layer.transform.y = y

    def set_layer_property(self, project: TTGProject, layer_id: str, key: str, value: Any) -> None:
        self.get_layer(project, layer_id).properties[key] = value

    def save_project(self, project: TTGProject, path: str | Path) -> None:
        project.save(path)

    def load_project(self, path: str | Path) -> TTGProject:
        return TTGProject.load(path)
