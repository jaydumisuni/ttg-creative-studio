#!/usr/bin/env python3
"""Self-test Banana Level deterministic workflows."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_action_engine import ActionEngine
from ttg_banana_actions import BananaActions
from ttg_banana_level import workflow_ids


def main() -> int:
    action = ActionEngine()
    banana = BananaActions()
    project = action.new_project("Banana Self Test", "image")
    text = action.add_text(project, "THETECHGUY", 100, 100)
    action.add_shape(project, "rectangle", 100, 240)
    banana.make_it_pop(project)
    banana.brand_everything(project)
    checks = [
        "make_it_pop" in workflow_ids(),
        "brand_everything" in workflow_ids(),
        text.type == "text3d",
        text.properties.get("glow") is True,
        text.properties.get("gradient") is True,
        project.export.get("banana", {}).get("last_workflow") == "brand_everything",
    ]
    if not all(checks):
        print("Banana Level self-test failed")
        print(checks)
        return 1
    print("Banana Level self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
