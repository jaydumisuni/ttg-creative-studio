#!/usr/bin/env python3
"""Offscreen smoke test for InteractiveCanvas widget wiring."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    from ttg_action_engine import ActionEngine
    from ttg_interactive_canvas import InteractiveCanvas

    app = QApplication.instance() or QApplication([])
    action = ActionEngine()
    project = action.new_project("Interactive Canvas Widget Self Test", "image")
    layer = action.add_shape(project, "rectangle", 100, 100)
    layer.properties["width"] = 200
    layer.properties["height"] = 100
    canvas = InteractiveCanvas(ROOT)
    canvas.resize(640, 420)
    canvas.set_project(project, layer.id)
    app.processEvents()
    checks = [
        canvas.project is project,
        canvas.selected_layer_id == layer.id,
        canvas.interaction.active_layer_id() == layer.id,
        canvas.minimumWidth() >= 640,
        canvas.hasMouseTracking(),
    ]
    if not all(checks):
        print("Interactive canvas widget self-test failed")
        print(checks)
        return 1
    print("Interactive canvas widget self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
