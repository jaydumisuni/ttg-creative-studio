#!/usr/bin/env python3
"""Print TTG Creative Studio product direction report."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_product_targets import TARGETS
from ttg_user_modes import MODES
from ttg_tool_registry import TOOLS, status_counts


def main() -> int:
    print("TTG Creative Studio Direction")
    print("=============================")
    print("Target: Photoshop power + Canva simplicity + Filmora motion")
    print("")
    print("Targets:")
    for target in TARGETS:
        print(f"- {target.name}: {target.promise}")
    print("")
    print("Modes:")
    for mode in MODES:
        print(f"- {mode.name}: {mode.description}")
    print("")
    print("Tools:")
    for tool in TOOLS:
        print(f"- {tool.label} [{tool.mode}/{tool.status}]: {tool.description}")
    print("")
    print("Status counts:", status_counts())
    if len(TARGETS) < 3 or len(MODES) < 3 or len(TOOLS) < 8:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
