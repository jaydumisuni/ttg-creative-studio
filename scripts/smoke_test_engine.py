#!/usr/bin/env python3
"""Smoke test the TTG Creative Studio engine without launching the UI."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_export_service import ExportService
from ttg_intro_builder import IntroBuilder
from ttg_project_schema import TTGProject
from ttg_render_plan import RenderPlanner
from ttg_validation import ProjectValidator


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        project_path = temp_path / "intro.ttgstudio.json"
        png_path = temp_path / "preview.png"
        frames_dir = temp_path / "frames"

        project = IntroBuilder().build_ttg_intro()
        project.canvas.width = 640
        project.canvas.height = 360
        project.canvas.fps = 6
        project.canvas.duration = 1.0
        project.save(project_path)

        loaded = TTGProject.load(project_path)
        validator = ProjectValidator()
        messages = validator.validate(loaded, ROOT)
        errors = [item for item in messages if item.level == "error"]
        if errors:
            for error in errors:
                print(f"ERROR: {error.message}")
            return 1

        plan = RenderPlanner().create_plan(loaded)
        if not plan.tasks:
            print("ERROR: render plan has no tasks")
            return 1

        service = ExportService(ROOT)
        service.export_png(loaded, png_path)
        if not png_path.exists() or png_path.stat().st_size <= 0:
            print("ERROR: PNG export failed")
            return 1

        frames = service.export_frames(loaded, frames_dir)
        if len(frames) != 6:
            print(f"ERROR: expected 6 frames, got {len(frames)}")
            return 1

    print("TTG Creative Studio engine smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
