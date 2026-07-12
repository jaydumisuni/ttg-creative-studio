#!/usr/bin/env python3
"""Build the final TTG Creative Studio release-decision report."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
REPORT = OUTPUTS / "RELEASE_DECISION.md"

REQUIRED_SOURCE = [
    "README.md",
    "src/ttg_creative_workspace.py",
    "src/ttg_property_engine.py",
    "src/ttg_interactive_canvas.py",
    "src/ttg_asset_package.py",
    "src/ttg_text_renderer.py",
    "src/ttg_image_intelligence.py",
    "scripts/review_gate_all.py",
    "scripts/review_claims_gate.py",
    "scripts/generate_visual_proof_package.py",
    "scripts/build_benchmark_gap_report.py",
    "docs/THETECHGUY_BUILDING_STANDARD.md",
    "docs/BENCHMARK_TARGETS.md",
    "docs/VISUAL_APPROVAL.json",
]

REQUIRED_OUTPUTS = [
    "ttg_reference_still.jpg",
    "ttg_reference_still_score.json",
    "reference_motion_contact_sheet.jpg",
    "reference_motion_preview.gif",
    "reference_motion_score.json",
    "ttg_visual_proof_manifest.json",
    "VISUAL_PROOF_REVIEW.md",
    "BENCHMARK_GAP_REPORT.md",
    "index.html",
]


def existing_nonempty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def load_json(path: Path) -> dict:
    if not existing_nonempty(path):
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> int:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    missing_source = [item for item in REQUIRED_SOURCE if not existing_nonempty(ROOT / item)]
    missing_outputs = [item for item in REQUIRED_OUTPUTS if not existing_nonempty(OUTPUTS / item)]
    ad_contact_sheet = OUTPUTS / "ad_workflow" / "ttg_ad_contact_sheet.jpg"
    if not existing_nonempty(ad_contact_sheet):
        missing_outputs.append("ad_workflow/ttg_ad_contact_sheet.jpg")

    manifest = load_json(OUTPUTS / "ttg_visual_proof_manifest.json")
    still = load_json(OUTPUTS / "ttg_reference_still_score.json")
    motion = load_json(OUTPUTS / "reference_motion_score.json")

    engine_closed = not missing_source
    automated_visual_pass = still.get("passed") is True and motion.get("passed") is True and manifest.get("automated_status") == "passed"
    human_visual_pass = manifest.get("human_approval") == "approved"
    visual_closed = not missing_outputs and automated_visual_pass and human_visual_pass
    release_candidate = engine_closed and visual_closed

    blockers = []
    if not automated_visual_pass:
        blockers.append("Automated still/motion visual guardrails have not all passed.")
    if not human_visual_pass:
        blockers.append("Explicit human visual approval is missing or pending.")

    lines = [
        "# TTG Creative Studio Release Decision",
        "",
        f"- Engine/workflow closure: {'PASS' if engine_closed else 'FAIL'}",
        f"- Automated visual guardrails: {'PASS' if automated_visual_pass else 'FAIL'}",
        f"- Human visual approval: {'PASS' if human_visual_pass else 'PENDING'}",
        f"- Visual proof closure: {'PASS' if visual_closed else 'FAIL'}",
        f"- Release-candidate decision: {'PASS' if release_candidate else 'BLOCKED'}",
        "",
        "## Meaning",
        "",
        "A PASS requires implementation/review files, non-empty visual artifacts, passing still/motion guardrails, the composed ad proof, and explicit visual approval.",
        "",
        "The clean GitHub Actions checkout provides reproducible runtime proof. Target-machine installation remains the final environment confirmation.",
        "",
        "## Missing source/review requirements",
        "",
    ]
    lines.extend(f"- {item}" for item in missing_source) if missing_source else lines.append("- None")
    lines.extend(["", "## Missing generated visual artifacts", ""])
    lines.extend(f"- {item}" for item in missing_outputs) if missing_outputs else lines.append("- None")
    lines.extend(["", "## Visual blockers", ""])
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- None")
    lines.extend([
        "",
        "## Final gate",
        "",
        "```powershell",
        "python scripts\\review_gate_all.py",
        "```",
        "",
        "The command must complete without an unexpected failure in a clean checkout.",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Release decision written: {REPORT}")
    print(f"Release candidate: {'PASS' if release_candidate else 'BLOCKED'}")
    return 0 if release_candidate else 1


if __name__ == "__main__":
    raise SystemExit(main())
