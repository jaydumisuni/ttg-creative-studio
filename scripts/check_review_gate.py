#!/usr/bin/env python3
"""Check whether visual proof review gate is open for video proof work."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
REVIEW = OUT / "ttg_visual_review.json"
MANIFEST = OUT / "ttg_visual_proof_manifest.json"


def main() -> int:
    if not MANIFEST.exists():
        print("Video proof blocked: missing visual proof manifest.")
        return 1
    if not REVIEW.exists():
        print("Video proof blocked: missing outputs/ttg_visual_review.json")
        return 1
    data = json.loads(REVIEW.read_text(encoding="utf-8"))
    checks = [
        data.get("review") == "accepted_for_video_proof",
        data.get("still_checked") is True,
        data.get("contact_sheet_checked") is True,
        data.get("gif_checked") is True,
        data.get("release_ready") is False,
    ]
    if not all(checks):
        print("Video proof blocked: review file is incomplete or invalid.")
        print(data)
        return 1
    print("Review gate open for video proof work. Release remains blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
