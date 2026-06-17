#!/usr/bin/env python3
"""Test manual layer editing and timeline action presets."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_action_engine import ActionEngine
from ttg_timeline_actions import TimelineActions


def main() -> int:
    actions = ActionEngine()
    timeline = TimelineActions()
    project = actions.new_project("Editing Test", "motion")
    project.canvas.duration = 2.0

    text = actions.add_text(project, "TEST", 100, 100)
    shape = actions.add_shape(project, "rectangle", 200, 200)
    if len(project.layers) != 2:
        print("ERROR: expected two layers")
        return 1

    dup = actions.duplicate_layer(project, text.id)
    if len(project.layers) != 3 or dup.id == text.id:
        print("ERROR: duplicate layer failed")
        return 1

    actions.offset_layer(project, dup.id, 10, -20)
    if dup.transform.x != text.transform.x + 40 or dup.transform.y != text.transform.y + 10:
        print("ERROR: offset layer failed")
        return 1

    actions.move_layer_order(project, dup.id, 1)
    actions.remove_layer(project, shape.id)
    if any(layer.id == shape.id for layer in project.layers):
        print("ERROR: remove layer failed")
        return 1

    timeline.add_fly_in_left(project, text.id, 0.0, 1.0)
    timeline.add_pulse(project, dup.id, 0.0, 2.0)
    if "position" not in text.keyframes or "opacity" not in text.keyframes:
        print("ERROR: fly-in preset failed")
        return 1
    if "scale" not in dup.keyframes:
        print("ERROR: pulse preset failed")
        return 1

    timeline.clear_animation(project, dup.id)
    if dup.keyframes:
        print("ERROR: clear animation failed")
        return 1

    print("TTG Creative Studio editing actions test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
