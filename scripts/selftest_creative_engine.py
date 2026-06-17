#!/usr/bin/env python3
"""Self-test for the TTG Creative Studio foundation modules."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_action_engine import ActionEngine
from ttg_canvas_engine import CanvasRenderer, RenderContext
from ttg_motion_exporter import MotionExporter
from ttg_pack_manager import PackFile, PackManifest, PackManager
from ttg_project_schema import TTGProject, make_ttg_intro_project
from ttg_timeline_engine import TimelineEngine


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        action = ActionEngine()
        project = action.new_project("Self Test", "motion")
        project.canvas.width = 640
        project.canvas.height = 360
        project.canvas.fps = 10
        project.canvas.duration = 1
        text = action.add_text(project, "THETECHGUY", 20, 30)
        action.add_keyframe(project, text.id, "position", 0.0, [20, 30, 0])
        action.add_keyframe(project, text.id, "position", 1.0, [120, 90, 0])
        action.add_shape(project, "rectangle", 40, 120)

        project_path = temp_path / "selftest.ttgstudio.json"
        project.save(project_path)
        loaded = TTGProject.load(project_path)
        assert_true(len(loaded.layers) == 2, "project save/load should preserve layers")

        timeline = TimelineEngine()
        moved = timeline.apply_to_layer(loaded.layers[0], 0.5)
        assert_true(moved.transform.x > 20, "timeline should move layer between keyframes")

        context = RenderContext(project_root=temp_path)
        image = CanvasRenderer(context).render(loaded, time=0.5)
        assert_true(image.size == (640, 360), "canvas render should match project size")

        frames = MotionExporter(context).export_frames(loaded, temp_path / "frames", limit_frames=2)
        assert_true(len(frames) == 2 and frames[0].exists(), "motion exporter should create preview frames")

        intro = make_ttg_intro_project()
        assert_true(any(layer.id == "wordmark" for layer in intro.layers), "intro template should include wordmark layer")

        manager = PackManager(temp_path / "appdata")
        manifest = PackManifest(
            id="test-pack",
            name="Test Pack",
            version="0.1.0",
            kind="asset",
            files=[PackFile(name="placeholder", url="", path="placeholder.txt")],
        )
        manager.save_manifest(manifest)
        assert_true(manager.is_installed("test-pack"), "pack manager should record installed packs")

    print("TTG Creative Studio self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
