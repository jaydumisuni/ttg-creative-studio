#!/usr/bin/env python3
"""Block video proof work unless the visual review gate is intentionally opened."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
REVIEW = OUT / "ttg_visual_review.json"
MANIFEST = OUT / "ttg_visual_proof_manifest.json"


def main() -> int:
    if not MANIFEST.exists():
        print("VIDEO BLOCKED: visual proof manifest is missing.")
        return 1
    if not REVIEW.exists():
        print("VIDEO BLOCKED: outputs/ttg_visual_review.json is missing.")
        print("Review the still, contact sheet and GIF before creating that file.")
        return 1
    data = json.loads(REVIEW.read_text(encoding="utf-8"))
    required = {
        "review": "accepted_for_video_proof",
        "still_checked": True,
        "contact_sheet_checked": True,
        "gif_checked": True,
        "release_ready": False,
    }
    for key, value in required.items():
        if data.get(key) != value:
            print(f"VIDEO BLOCKED: review field {key!r} must be {value!r}.")
            return 1
    print("VIDEO GATE OPEN: video proof work may proceed. Release remains blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
