#!/usr/bin/env python3
"""Build a human-readable visual proof review summary."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
SUMMARY = OUT / "VISUAL_PROOF_REVIEW.md"


def load_json(name: str) -> dict:
    path = OUT / name
    if not path.exists():
        return {"missing": True}
    return json.loads(path.read_text(encoding="utf-8"))


def yes_no(value: object) -> str:
    return "yes" if value else "no"


def main() -> int:
    still = load_json("ttg_reference_still_score.json")
    motion = load_json("reference_motion_score.json")
    manifest = load_json("ttg_visual_proof_manifest.json")

    lines = [
        "# TTG Visual Proof Review",
        "",
        "This package is for visual review only. It does not make Creative Studio release-ready.",
        "",
        "## Generated artifacts",
        "",
        "- `ttg_reference_still.jpg`",
        "- `reference_motion_contact_sheet.jpg`",
        "- `reference_motion_preview.gif`",
        "- `ttg_reference_still_score.json`",
        "- `reference_motion_score.json`",
        "- `ttg_visual_proof_manifest.json`",
        "",
        "## Still score",
        "",
        f"- Passed guardrails: {yes_no(still.get('passed'))}",
        f"- Resolution: {still.get('width', 'n/a')} x {still.get('height', 'n/a')}",
        f"- Contrast: {still.get('contrast', 'n/a')}",
        f"- Neon ratio: {still.get('neon_ratio', 'n/a')}",
        f"- Detail score: {still.get('detail_score', 'n/a')}",
        "",
        "## Motion score",
        "",
        f"- Passed guardrails: {yes_no(motion.get('passed'))}",
        f"- Frame count: {motion.get('frame_count', 'n/a')}",
        f"- Motion score: {motion.get('motion_score', 'n/a')}",
        f"- Final contrast: {motion.get('final_contrast', 'n/a')}",
        "",
        "## Gate status",
        "",
        f"- Automated status: {manifest.get('automated_status', 'unknown')}",
        f"- Human approval: {manifest.get('human_approval', 'pending')}",
        f"- Video export: {manifest.get('video_export', 'blocked_until_human_approval')}",
        f"- Release packaging: {manifest.get('release_packaging', 'blocked_until_human_approval')}",
        "",
        "## Human review checklist",
        "",
        "- Ghost/logo is visible and correct.",
        "- THETECHGUY wordmark feels premium, not flat 2D text.",
        "- SYSTEMS / TOOLS / ISP / WEB cards look intentional.",
        "- Scene has depth, glow, floor/perspective, and reflections.",
        "- Animated preview feels alive, not only a static zoom.",
        "- No random text was added on top of the art.",
        "",
        "## Next decision",
        "",
        "If the still/contact sheet/GIF are not good enough, improve the renderer and template first.",
        "If they are good enough, create the local review gate file and move only to video proof, not release.",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved review summary: {SUMMARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
