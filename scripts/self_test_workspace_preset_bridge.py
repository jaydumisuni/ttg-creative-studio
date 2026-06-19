#!/usr/bin/env python3
"""Static/self-test for Advanced Mode workspace preset bridge."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_advanced_panel import AdvancedModePanel
from ttg_workspace_preset_bridge import LAYER_PRESET_GROUPS, PROJECT_PRESET_GROUPS


def main() -> int:
    checks = [
        hasattr(AdvancedModePanel, "presetRequested"),
        "Text Material" in LAYER_PRESET_GROUPS,
        "Effects" in LAYER_PRESET_GROUPS,
        "Scene" in PROJECT_PRESET_GROUPS,
        "Motion" in PROJECT_PRESET_GROUPS,
        "Export" in PROJECT_PRESET_GROUPS,
    ]
    if not all(checks):
        print("Workspace preset bridge self-test failed")
        return 1
    print("Workspace preset bridge self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
