#!/usr/bin/env python3
"""Render and score the repo-native THETECHGUY reference still."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_reference_still_renderer import render_reference_still
from score_reference_still import score_image


def main() -> int:
    output = ROOT / "outputs" / "ttg_reference_still.jpg"
    report = ROOT / "outputs" / "ttg_reference_still_score.json"
    render_reference_still(ROOT, output)
    result = score_image(output)
    report.write_text(__import__("json").dumps(result, indent=2), encoding="utf-8")
    print(f"Rendered: {output}")
    print(f"Score report: {report}")
    print(f"Passed: {result['passed']}")
    if not result["passed"]:
        print("Reference still did not meet repo-side quality guardrails.")
        print(result)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
