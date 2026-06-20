#!/usr/bin/env python3
"""Self-test canvas selection, move, resize and rotate math."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_action_engine import ActionEngine
from ttg_canvas_tools import ResizeHandle, SelectionState, hit_test, layer_rect, move_layer, resize_layer, rotate_layer, selection_bounds


def main() -> int:
    action = ActionEngine()
    project = action.new_project("Canvas Tool Self Test", "image")
    layer = action.add_shape(project, "rectangle", 100, 100)
    layer.properties["width"] = 200
    layer.properties["height"] = 100

    selected = hit_test(project, 150, 130)
    state = SelectionState([])
    state.select(selected)
    move_layer(layer, 13, 17, snap_enabled=True, grid=10)
    rect_after_move = layer_rect(layer)
    resize_layer(layer, ResizeHandle.BOTTOM_RIGHT, 54, 31, snap_enabled=True, grid=10)
    rect_after_resize = layer_rect(layer)
    rotate_layer(layer, rect_after_resize.cx, rect_after_resize.cy, rect_after_resize.cx, rect_after_resize.cy + 100, snap_enabled=True, step=5)
    bounds = selection_bounds(project, [layer.id])

    checks = [
        selected == layer.id,
        state.active_layer_id == layer.id,
        rect_after_move.x == 110,
        rect_after_move.y == 120,
        rect_after_resize.width == 250,
        rect_after_resize.height == 130,
        layer.transform.rotation_z == 90,
        bounds is not None and bounds.width == 250 and bounds.height == 130,
    ]
    if not all(checks):
        print("Canvas tools self-test failed")
        print(checks)
        print(layer)
        return 1
    print("Canvas tools self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
