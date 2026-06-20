#!/usr/bin/env python3
"""Import-level smoke test for app/window wiring."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def main() -> int:
    from ttg_creative_app import CreativeStudioWindow  # noqa: F401
    from ttg_workspace_preset_bridge import install_preset_bridge  # noqa: F401

    print("App wiring import self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
