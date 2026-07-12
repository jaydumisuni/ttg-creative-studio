#!/usr/bin/env python3
"""Generate and verify TTG Creative Studio visual proof artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_reference_still_renderer import render_reference_still
from ttg_reference_motion_renderer import render_reference_motion_frames
from score_reference_still import score_image

REQUIRED_VISUAL_PROOF_ARTIFACTS = [
    ROOT / "outputs" / "ttg_reference_still.jpg",
    ROOT / "outputs" / "ttg_reference_still_score.json",
    ROOT / "outputs" / "reference_motion_contact_sheet.jpg",
    ROOT / "outputs" / "reference_motion_preview.gif",
    ROOT / "outputs" / "reference_motion_score.json",
    ROOT / "outputs" / "ttg_visual_proof_manifest.json",
    ROOT / "outputs" / "VISUAL_PROOF_REVIEW.md",
    ROOT / "outputs" / "ADVANCED_PRESET_REPORT.md",
    ROOT / "outputs" / "index.html",
]


def verify_visual_artifacts() -> bool:
    missing = [path for path in REQUIRED_VISUAL_PROOF_ARTIFACTS if not path.exists() or path.stat().st_size <= 0]
    if missing:
        print("Missing visual proof artifacts:")
        for path in missing:
            print(f"- {path}")
        return False
    return True


def main() -> int:
    outputs = ROOT / "outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    still = outputs / "ttg_reference_still.jpg"
    still_report = outputs / "ttg_reference_still_score.json"
    render_reference_still(ROOT, still)
    still_score = score_image(still)
    still_report.write_text(json.dumps(still_score, indent=2), encoding="utf-8")
    print(json.dumps(still_score, indent=2))
    if not still_score.get("passed"):
        print("ERROR: reference still failed visual guardrails")
        return 1

    frames_dir = outputs / "reference_motion_frames"
    frames = render_reference_motion_frames(ROOT, frames_dir, frames=72)
    if len(frames) != 72:
        print(f"ERROR: expected 72 frames, got {len(frames)}")
        return 1
    if not all(path.exists() and path.stat().st_size > 0 for path in frames):
        print("ERROR: one or more rendered frames are missing or empty")
        return 1

    from build_motion_contact_sheet import main as build_sheet
    from score_reference_motion import main as score_motion
    from build_motion_gif_preview import main as build_gif
    from build_proof_manifest import main as build_manifest
    from build_review_summary import main as build_summary
    from build_artifact_index import main as build_index
    from build_preset_report import main as build_presets

    if build_sheet() != 0:
        return 1
    if score_motion() != 0:
        return 1
    if build_gif() != 0:
        return 1
    build_manifest()
    build_summary()
    build_presets()
    build_index()
    if not verify_visual_artifacts():
        return 1
    print("Visual proof package generated and guardrails passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
