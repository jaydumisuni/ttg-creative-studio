#!/usr/bin/env python3
"""Fast structural self-check for the visual proof and Advanced Mode pipeline."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "src/ttg_reference_still_renderer.py",
    "src/ttg_reference_motion_renderer.py",
    "src/ttg_advanced_presets.py",
    "src/ttg_preset_actions.py",
    "scripts/self_test_presets.py",
    "scripts/generate_visual_proof_package.py",
    "scripts/build_motion_contact_sheet.py",
    "scripts/build_motion_gif_preview.py",
    "scripts/build_artifact_index.py",
    "scripts/build_review_summary.py",
    "scripts/build_preset_report.py",
    "scripts/proof_status.py",
    "scripts/check_video_gate.py",
    "scripts/build_video_proof.py",
    "docs/VISUAL_APPROVAL_GATE.md",
    "docs/VIDEO_PROOF_STAGE.md",
    "docs/NO_RELEASE_UNTIL.md",
    "docs/ADVANCED_MODE_PRESETS.md",
    "packs/video-export-pack.json",
    ".github/workflows/reference-preview.yml",
]


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    print("TTG visual pipeline structural self-check")
    print("========================================")
    if missing:
        print("Missing files:")
        for path in missing:
            print(f"  - {path}")
        return 1
    print(f"All required files present: {len(REQUIRED)}")
    print("Render proof still happens in generate_visual_proof_package.py / GitHub Actions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
