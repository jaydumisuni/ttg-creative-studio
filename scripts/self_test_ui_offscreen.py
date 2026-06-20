#!/usr/bin/env python3
"""Offscreen UI smoke test for TTG Creative Studio.

This creates QApplication + CreativeStudioWindow using Qt offscreen mode,
verifies the central workspace exists, and closes immediately. It catches real
constructor/layout/import issues without requiring a visible desktop.
"""

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
    from ttg_creative_app import CreativeStudioWindow

    app = QApplication.instance() or QApplication([])
    window = CreativeStudioWindow()
    workspace = window.centralWidget()
    checks = [
        window.windowTitle() == "TTG Creative Studio",
        workspace is not None,
        hasattr(workspace, "advanced"),
        hasattr(workspace, "canvas"),
        hasattr(workspace, "properties"),
        hasattr(workspace, "preset_actions"),
    ]
    window.close()
    app.processEvents()
    if not all(checks):
        print("Offscreen UI smoke test failed")
        print(checks)
        return 1
    print("Offscreen UI smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
