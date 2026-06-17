#!/usr/bin/env python3
"""Generate TTG Creative Studio capability report."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_capabilities import save_report


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "CAPABILITIES.md"
    save_report(ROOT, output)
    print(f"Saved capability report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
