#!/usr/bin/env python3
"""Self-test Qt-facing canvas interaction controller without launching UI."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_action_engine import ActionEngine
from ttg_canvas_interaction import CanvasInteractionController, DragMode
from ttg_canvas_tools import ResizeHandle, layer_rect


def main() -> int:
    action = ActionEngine()
    project = action.new_project("Canvas Interaction Self Test", "image")
    layer = action.add_shape(project, "rectangle", 50, 50)
    layer.properties["width"] = 150
    layer.properties["height"] = 90

    controller = CanvasInteractionController(project)
    selected = controller.mouse_press(75, 75)
    changed = controller.mouse_move(87, 91)
    released = controller.mouse_release(101, 113)
    rect = layer_rect(layer)

    controller.mouse_press(rect.right, rect.bottom, mode=DragMode.RESIZE, resize_handle=ResizeHandle.BOTTOM_RIGHT)
    resize_changed = controller.mouse_move(rect.right + 42, rect.bottom + 28)
    controller.mouse_release(rect.right + 42, rect.bottom + 28)
    resized = layer_rect(layer)

    controller.mouse_press(resized.cx, resized.y - 40, mode=DragMode.ROTATE)
    rotate_changed = controller.mouse_move(resized.cx, resized.cy + 140)
    controller.mouse_release(resized.cx, resized.cy + 140)

    checks = [
        selected == layer.id,
        controller.active_layer_id() == layer.id,
        changed is True,
        released is True,
        rect.x == 80,
        rect.y == 90,
        resize_changed is True,
        resized.width == 190,
        resized.height == 120,
        rotate_changed is True,
        layer.transform.rotation_z == 90,
    ]
    if not all(checks):
        print("Canvas interaction self-test failed")
        print(checks)
        print(layer)
        return 1
    print("Canvas interaction self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
