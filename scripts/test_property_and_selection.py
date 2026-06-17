#!/usr/bin/env python3
"""Test property editing and canvas selection helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_action_engine import ActionEngine
from ttg_canvas_selection import CanvasSelection
from ttg_property_actions import PropertyActions


def main() -> int:
    actions = ActionEngine()
    props = PropertyActions()
    select = CanvasSelection()
    project = actions.new_project("Property Test", "image")
    text = actions.add_text(project, "OLD", 100, 100)
    shape = actions.add_shape(project, "rectangle", 110, 110)

    props.set_text(project, text.id, "NEW TEXT")
    props.set_size(project, text.id, 48)
    props.set_color(project, text.id, "#00E5FF")
    props.set_position(project, text.id, 20, 30)
    props.set_scale(project, text.id, 1.5)
    props.set_opacity(project, text.id, 0.5)

    if text.properties.get("text") != "NEW TEXT":
        print("ERROR: text property not updated")
        return 1
    if text.transform.x != 20 or text.transform.y != 30:
        print("ERROR: position property not updated")
        return 1
    if text.transform.opacity != 0.5:
        print("ERROR: opacity property not updated")
        return 1

    # Shape is topmost and overlaps this point, so hit-test should choose shape.
    hit = select.hit_test(project, 120, 120)
    if hit != shape.id:
        print(f"ERROR: expected topmost shape hit, got {hit}")
        return 1

    shape.visible = False
    hit = select.hit_test(project, 25, 35)
    if hit != text.id:
        print(f"ERROR: expected text hit, got {hit}")
        return 1

    print("TTG Creative Studio property and selection test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
