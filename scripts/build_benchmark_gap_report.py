#!/usr/bin/env python3
"""Build a benchmark gap report from current TTG visual proof artifacts."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
REPORT = OUTPUTS / "BENCHMARK_GAP_REPORT.md"

BENCHMARKS = [
    {
        "target": "Penpot / tldraw / Excalidraw class",
        "task": "Editable canvas, direct manipulation, handles and approachable layout workflow.",
        "proof": "ttg_reference_still.jpg, UI/offscreen workflow tests, canvas interaction tests",
        "current_gap": "Canvas engine exists, but final professional editor feel, cursor states, guides and multi-select polish still need visual comparison.",
        "next": "Use benchmark editor feel to tune snapping, handles, guides and layer manipulation UX.",
    },
    {
        "target": "CreatiPoster class",
        "task": "Turn asset package into editable poster/ad project.",
        "proof": "ttg_ad_from_zip.ttgstudio.json, ttg_ad_contact_sheet.jpg, app ad ZIP import test",
        "current_gap": "Ad ZIP workflow exists, but visual template quality and automatic layout intelligence must improve against real poster/ad examples.",
        "next": "Add benchmark-style layout scoring: hierarchy, spacing, CTA prominence, brand consistency and safe margins.",
    },
    {
        "target": "OpenShot / Kdenlive / Flowblade / Shotcut class",
        "task": "Timeline, preview, tracks, keyframes and export workflow.",
        "proof": "reference_motion_contact_sheet.jpg, reference_motion_preview.gif, frame export path, video gate",
        "current_gap": "Timeline primitives and proof preview exist, but full track editor, trimming and polished playback UI are still below NLE benchmarks.",
        "next": "Build track-based timeline UI after engine proof, with visible keyframes, playhead and clip handles.",
    },
    {
        "target": "Remotion / Motion Canvas class",
        "task": "Repeatable code-driven motion templates and reproducible renders.",
        "proof": "reference_motion_frames, reference_motion_preview.gif, visual proof manifest",
        "current_gap": "Motion render proof exists, but template parametrization and programmable scene systems need stronger abstraction.",
        "next": "Create reusable motion-template definitions for ads, intros and product explainers.",
    },
    {
        "target": "Blender class",
        "task": "True cinematic 3D text, camera, lights, depth and particles.",
        "proof": "ttg_reference_still.jpg, reference_motion_preview.gif",
        "current_gap": "Current renderer is still mostly 2D/2.5D. True 3D depth/camera/lighting remains the biggest cinematic gap.",
        "next": "Add a 3D renderer bridge or dedicated cinematic scene engine for title depth, camera moves, lighting and particles.",
    },
]


def artifact_state(name: str) -> str:
    path = OUTPUTS / name
    if path.exists() and path.stat().st_size > 0:
        return f"present ({path.stat().st_size} bytes)"
    return "missing until visual proof generation runs"


def main() -> int:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    lines = [
        "# TTG Creative Studio Benchmark Gap Report",
        "",
        "This report turns ahead-of-us benchmark tools into practical TTG engineering targets.",
        "",
        "## Current visual artifact state",
        "",
    ]
    for artifact in [
        "ttg_reference_still.jpg",
        "reference_motion_contact_sheet.jpg",
        "reference_motion_preview.gif",
        "ttg_visual_proof_manifest.json",
        "VISUAL_PROOF_REVIEW.md",
        "ttg_ad_contact_sheet.jpg",
    ]:
        lines.append(f"- {artifact}: {artifact_state(artifact)}")
    lines.extend(["", "## Benchmark gaps", ""])
    for item in BENCHMARKS:
        lines.extend([
            f"### {item['target']}",
            "",
            f"- Task attempted: {item['task']}",
            f"- TTG proof: {item['proof']}",
            f"- Gap found: {item['current_gap']}",
            f"- Next implementation target: {item['next']}",
            "",
        ])
    lines.extend([
        "## Rule",
        "",
        "Benchmark reports are not marketing. They are engineering pressure.",
        "",
        "If TTG output looks or feels worse than the benchmark class, the difference becomes the next build target.",
    ])
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Benchmark gap report written: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
