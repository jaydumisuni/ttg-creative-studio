#!/usr/bin/env python3
"""Print a compact status for the visual proof package."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
REQUIRED = [
    "index.html",
    "VISUAL_PROOF_REVIEW.md",
    "ttg_reference_still.jpg",
    "ttg_reference_still_score.json",
    "reference_motion_preview.gif",
    "reference_motion_contact_sheet.jpg",
    "reference_motion_score.json",
    "ttg_visual_proof_manifest.json",
]


def load_json(name: str) -> dict:
    path = OUT / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> int:
    missing = [name for name in REQUIRED if not (OUT / name).exists()]
    still = load_json("ttg_reference_still_score.json")
    motion = load_json("reference_motion_score.json")
    manifest = load_json("ttg_visual_proof_manifest.json")

    print("TTG Visual Proof Status")
    print("=======================")
    print(f"Package complete: {'no' if missing else 'yes'}")
    if missing:
        print("Missing:")
        for name in missing:
            print(f"  - {name}")
    print(f"Still guardrails passed: {still.get('passed', 'unknown')}")
    print(f"Motion guardrails passed: {motion.get('passed', 'unknown')}")
    print(f"Automated status: {manifest.get('automated_status', 'unknown')}")
    print(f"Human approval: {manifest.get('human_approval', 'pending')}")
    print(f"Video export: {manifest.get('video_export', 'blocked')}")
    print(f"Release packaging: {manifest.get('release_packaging', 'blocked')}")
    if missing:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
