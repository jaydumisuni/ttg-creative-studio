#!/usr/bin/env python3
"""Validation helpers for TTG Creative Studio projects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ttg_project_schema import TTGProject


@dataclass
class ValidationMessage:
    level: str
    message: str
    target: str = "project"


class ProjectValidator:
    def validate(self, project: TTGProject, project_root: str | Path | None = None) -> list[ValidationMessage]:
        messages: list[ValidationMessage] = []
        if project.canvas.width <= 0 or project.canvas.height <= 0:
            messages.append(ValidationMessage("error", "Canvas width and height must be positive."))
        if project.canvas.fps <= 0:
            messages.append(ValidationMessage("error", "FPS must be positive."))
        if project.canvas.duration <= 0:
            messages.append(ValidationMessage("error", "Duration must be positive."))
        seen: set[str] = set()
        for layer in project.layers:
            if layer.id in seen:
                messages.append(ValidationMessage("error", f"Duplicate layer id: {layer.id}", layer.id))
            seen.add(layer.id)
            if layer.transform.opacity < 0 or layer.transform.opacity > 1:
                messages.append(ValidationMessage("warning", f"Opacity should be between 0 and 1: {layer.name}", layer.id))
            if layer.type == "image":
                asset_path = layer.properties.get("path") or layer.properties.get("asset_path")
                if asset_path and project_root:
                    path = Path(asset_path)
                    if not path.is_absolute():
                        path = Path(project_root) / path
                    if not path.exists():
                        messages.append(ValidationMessage("warning", f"Image file missing: {asset_path}", layer.id))
            for prop, frames in layer.keyframes.items():
                last_time = -1.0
                for frame in frames:
                    if frame.time < 0:
                        messages.append(ValidationMessage("error", f"Negative keyframe time on {layer.name}/{prop}", layer.id))
                    if frame.time < last_time:
                        messages.append(ValidationMessage("warning", f"Keyframes are not sorted on {layer.name}/{prop}", layer.id))
                    last_time = frame.time
        return messages

    def is_valid(self, project: TTGProject, project_root: str | Path | None = None) -> bool:
        return not any(item.level == "error" for item in self.validate(project, project_root))
