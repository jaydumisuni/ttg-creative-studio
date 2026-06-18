#!/usr/bin/env python3
"""Build a proof manifest for generated TTG reference artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
MANIFEST = OUT / "ttg_visual_proof_manifest.json"

ARTIFACTS = [
    "ttg_reference_still.jpg",
    "ttg_reference_still_score.json",
    "reference_motion_score.json",
    "reference_motion_contact_sheet.jpg",
    "reference_motion_preview.gif",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    items = []
    missing = []
    for name in ARTIFACTS:
        path = OUT / name
        if not path.exists():
            missing.append(name)
            continue
        items.append({
            "name": name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    status = {
        "proof_stage": "visual-proof",
        "automated_status": "passed" if not missing else "incomplete",
        "human_approval": "pending",
        "video_export": "blocked_until_human_approval",
        "release_packaging": "blocked_until_human_approval",
        "missing": missing,
        "artifacts": items,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
