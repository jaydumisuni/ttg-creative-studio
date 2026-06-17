#!/usr/bin/env python3
"""Test undo/redo history."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_action_engine import ActionEngine
from ttg_history import ProjectHistory


def main() -> int:
    actions = ActionEngine()
    history = ProjectHistory()
    project = actions.new_project("History Test", "image")

    history.remember("before add", project)
    actions.add_text(project, "A", 10, 10)
    if len(project.layers) != 1:
        print("ERROR: add text failed")
        return 1

    project = history.undo(project)
    if len(project.layers) != 0:
        print("ERROR: undo failed")
        return 1

    project = history.redo(project)
    if len(project.layers) != 1:
        print("ERROR: redo failed")
        return 1

    print("TTG Creative Studio history test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
