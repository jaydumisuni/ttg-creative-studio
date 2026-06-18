#!/usr/bin/env python3
"""Render the repo-native THETECHGUY reference still."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_reference_still_renderer import render_reference_still


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs" / "ttg_reference_still.jpg"
    path = render_reference_still(ROOT, output)
    print(f"Rendered reference still: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
