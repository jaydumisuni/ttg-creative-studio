#!/usr/bin/env python3
"""Render repo-native THETECHGUY reference motion proof frames."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_reference_motion_renderer import render_reference_motion_frames


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "outputs" / "reference_motion_frames"
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 48
    paths = render_reference_motion_frames(ROOT, output, frames=frames)
    print(f"Rendered {len(paths)} reference motion frames to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
