#!/usr/bin/env python3
"""Build a proof manifest for generated TTG reference artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
MANIFEST = OUT / "ttg_visual_proof_manifest.json"
APPROVAL = ROOT / "docs" / "VISUAL_APPROVAL.json"

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


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> int:
    items = []
    missing = []
    for name in ARTIFACTS:
        path = OUT / name
        if not path.exists() or path.stat().st_size <= 0:
            missing.append(name)
            continue
        items.append({
            "name": name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

    still = load_json(OUT / "ttg_reference_still_score.json")
    motion = load_json(OUT / "reference_motion_score.json")
    approval = load_json(APPROVAL)
    automated_pass = not missing and still.get("passed") is True and motion.get("passed") is True
    human_approved = approval.get("status") == "approved"

    status = {
        "proof_stage": "visual-proof",
        "automated_status": "passed" if automated_pass else "incomplete",
        "human_approval": "approved" if human_approved else "pending",
        "visual_reviewer": approval.get("reviewer"),
        "visual_review_date": approval.get("date"),
        "visual_review_notes": approval.get("notes", []),
        "video_export": "approved_for_video_proof" if automated_pass and human_approved else "blocked_until_human_approval",
        "release_packaging": "approved_for_release_candidate" if automated_pass and human_approved else "blocked_until_human_approval",
        "missing": missing,
        "artifacts": items,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status, indent=2))
    return 0 if automated_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
