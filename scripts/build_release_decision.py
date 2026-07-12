#!/usr/bin/env python3
"""Build the final TTG Creative Studio release-decision report."""

from __future__ import annotations

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
]

REQUIRED_OUTPUTS = [
    "ttg_reference_still.jpg",
    "reference_motion_contact_sheet.jpg",
    "reference_motion_preview.gif",
    "ttg_visual_proof_manifest.json",
    "VISUAL_PROOF_REVIEW.md",
    "BENCHMARK_GAP_REPORT.md",
    "index.html",
]


def existing_nonempty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def main() -> int:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    missing_source = [item for item in REQUIRED_SOURCE if not existing_nonempty(ROOT / item)]
    missing_outputs = [item for item in REQUIRED_OUTPUTS if not existing_nonempty(OUTPUTS / item)]

    engine_closed = not missing_source
    visual_closed = not missing_outputs
    release_candidate = engine_closed and visual_closed

    lines = [
        "# TTG Creative Studio Release Decision",
        "",
        f"- Engine/workflow closure: {'PASS' if engine_closed else 'FAIL'}",
        f"- Visual proof closure: {'PASS' if visual_closed else 'FAIL'}",
        f"- Release-candidate decision: {'PASS' if release_candidate else 'BLOCKED'}",
        "",
        "## Meaning",
        "",
        "A PASS means the repository has the required implementation files and generated visual-review artifacts for a release-candidate handoff.",
        "",
        "It does not replace clean-clone and target-machine proof. Those remain the final confirmation step under the THETECHGUY Building Standard.",
        "",
        "## Missing source/review requirements",
        "",
    ]
    if missing_source:
        lines.extend(f"- {item}" for item in missing_source)
    else:
        lines.append("- None")
    lines.extend(["", "## Missing generated visual artifacts", ""])
    if missing_outputs:
        lines.extend(f"- {item}" for item in missing_outputs)
    else:
        lines.append("- None")
    lines.extend([
        "",
        "## Final gate",
        "",
        "```powershell",
        "python scripts\\review_gate_all.py",
        "```",
        "",
        "The review gate must complete without an unexpected failure before clean-clone/runtime proof begins.",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Release decision written: {REPORT}")
    print(f"Release candidate: {'PASS' if release_candidate else 'BLOCKED'}")
    return 0 if release_candidate else 1


if __name__ == "__main__":
    raise SystemExit(main())
