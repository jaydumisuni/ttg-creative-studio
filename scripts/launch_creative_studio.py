#!/usr/bin/env python3
"""Launch TTG Creative Studio from a source checkout."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_creative_app import run

raise SystemExit(run())
