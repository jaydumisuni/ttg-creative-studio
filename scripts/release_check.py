#!/usr/bin/env python3
"""Run TTG Creative Studio release readiness checks."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_release_check import ReleaseChecker


def main() -> int:
    result = ReleaseChecker(ROOT).run()
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")
    if result.passed:
        print("Release readiness check passed")
        return 0
    print("Release readiness check failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
