#!/usr/bin/env python3
"""Write a GitHub Actions step summary for the visual proof workflow."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"


def load(name: str) -> dict:
    path = OUT / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def exists(name: str) -> str:
    return "yes" if (OUT / name).exists() else "no"


def main() -> int:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        print("No GITHUB_STEP_SUMMARY set; skipping.")
        return 0
    still = load("ttg_reference_still_score.json")
    motion = load("reference_motion_score.json")
    manifest = load("ttg_visual_proof_manifest.json")
    lines = [
        "# TTG Creative Studio Visual Proof",
        "",
        "## Artifact checklist",
        "",
        f"- Still image: {exists('ttg_reference_still.jpg')}",
        f"- Contact sheet: {exists('reference_motion_contact_sheet.jpg')}",
        f"- GIF preview: {exists('reference_motion_preview.gif')}",
        f"- Review summary: {exists('VISUAL_PROOF_REVIEW.md')}",
        f"- Failure report: {exists('FAILURE_REPORT.md')}",
        "",
        "## Scores",
        "",
        f"- Still passed guardrails: {still.get('passed', 'unknown')}",
        f"- Still contrast: {still.get('contrast', 'n/a')}",
        f"- Still neon ratio: {still.get('neon_ratio', 'n/a')}",
        f"- Motion passed guardrails: {motion.get('passed', 'unknown')}",
        f"- Motion score: {motion.get('motion_score', 'n/a')}",
        "",
        "## Gate status",
        "",
        f"- Automated status: {manifest.get('automated_status', 'unknown')}",
        f"- Human approval: {manifest.get('human_approval', 'pending')}",
        f"- Video export: {manifest.get('video_export', 'blocked')}",
        f"- Release packaging: {manifest.get('release_packaging', 'blocked')}",
        "",
        "Download the artifact named `ttg-reference-animated-preview` and review `VISUAL_PROOF_REVIEW.md` first.",
    ]
    Path(summary_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote workflow summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
