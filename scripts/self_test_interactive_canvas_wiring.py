#!/usr/bin/env python3
"""Static wiring test for InteractiveCanvas controller integration."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANVAS = ROOT / "src" / "ttg_interactive_canvas.py"


def main() -> int:
    content = CANVAS.read_text(encoding="utf-8")
    checks = [
        "CanvasInteractionController" in content,
        "self.interaction = CanvasInteractionController" in content,
        "self.interaction.mouse_press" in content,
        "self.interaction.mouse_move" in content,
        "self.interaction.mouse_release" in content,
        "def _draw_handle" in content,
        "painter.drawEllipse" in content,
        "layerMoved.emit" in content,
    ]
    if not all(checks):
        print("InteractiveCanvas wiring self-test failed")
        print(checks)
        return 1
    print("InteractiveCanvas wiring self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
