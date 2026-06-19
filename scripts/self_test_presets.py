#!/usr/bin/env python3
"""Self-test Advanced Mode preset application without launching the UI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_action_engine import ActionEngine
from ttg_preset_actions import PresetActions


def main() -> int:
    action = ActionEngine()
    presets = PresetActions()
    project = action.new_project("Preset Self Test", "image")
    text = action.add_text(project, "THETECHGUY", 100, 100)
    shape = action.add_shape(project, "rectangle", 100, 240)

    presets.apply_to_layer(project, text.id, "neon_chrome")
    presets.apply_to_layer(project, shape.id, "glass_card")
    presets.apply_scene_preset(project, "cyber_floor")
    presets.apply_motion_preset(project, "dark_start_reveal")
    presets.apply_export_preset(project, "youtube_intro_1080p")

    checks = [
        text.type == "text3d",
        text.properties.get("advanced_preset") == "neon_chrome",
        shape.properties.get("advanced_preset") == "glass_card",
        project.metadata.get("scene_preset") == "cyber_floor",
        project.metadata.get("motion_preset") == "dark_start_reveal",
        project.metadata.get("export_preset") == "youtube_intro_1080p",
        project.canvas.width == 1920,
        project.canvas.height == 1080,
        project.canvas.fps == 30,
    ]
    if not all(checks):
        print("Preset self-test failed")
        print(project)
        return 1
    print("Preset self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
