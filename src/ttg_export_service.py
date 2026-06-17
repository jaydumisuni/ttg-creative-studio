#!/usr/bin/env python3
"""Export helpers for TTG Creative Studio."""

from __future__ import annotations

from pathlib import Path

from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_motion_exporter import MotionExporter
from ttg_project_schema import TTGProject
from ttg_validation import ProjectValidator


class ExportService:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.validator = ProjectValidator()

    def _ensure_valid(self, project: TTGProject) -> None:
        messages = self.validator.validate(project, self.project_root)
        errors = [item.message for item in messages if item.level == "error"]
        if errors:
            raise RuntimeError("Project has validation errors: " + "; ".join(errors))

    def export_png(self, project: TTGProject, output_path: str | Path) -> Path:
        self._ensure_valid(project)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        CanvasRenderer(RenderContext(project_root=self.project_root)).render(project).save(output_path)
        return output_path

    def export_frames(self, project: TTGProject, output_dir: str | Path) -> list[Path]:
        self._ensure_valid(project)
        return MotionExporter(RenderContext(project_root=self.project_root)).export_frames(project, output_dir)

    def export_mp4(self, project: TTGProject, output_path: str | Path, work_dir: str | Path) -> Path:
        self._ensure_valid(project)
        return MotionExporter(RenderContext(project_root=self.project_root)).export_mp4(project, output_path, work_dir)
