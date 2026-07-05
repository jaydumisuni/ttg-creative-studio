#!/usr/bin/env python3
"""Claims-vs-implementation review gate."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLAIMS = [
    {
        "claim": "THETECHGUY Building Standard exists",
        "docs": ["docs/THETECHGUY_BUILDING_STANDARD.md"],
        "code": ["scripts/building_standard_report.py"],
        "phrases": ["Finish, then prove", "Claims must match implementation"],
    },
    {
        "claim": "Engine first, UI last is documented",
        "docs": ["docs/UI_LAST_RULE.md", "docs/PRODUCT_STANDARD.md"],
        "code": ["scripts/review_gate_all.py"],
        "phrases": ["Engine first", "UI last"],
    },
    {
        "claim": "Property and timeline engines are implemented and tested",
        "docs": [],
        "code": ["src/ttg_property_engine.py", "scripts/check_property_schema.py"],
        "phrases": ["PropertyEdit", "set_layer_time", "add_layer_keyframe", "evaluate_keyframes"],
    },
    {
        "claim": "ZIP/folder asset import is implemented and tested",
        "docs": [],
        "code": ["src/ttg_asset_package.py", "scripts/self_test_asset_package.py"],
        "phrases": ["import_asset_package", "Unsafe ZIP path rejected"],
    },
    {
        "claim": "Ad ZIP/folder workflow creates editable project and visual proof",
        "docs": [],
        "code": [
            "scripts/build_ad_project_from_assets.py",
            "scripts/run_ad_workflow.py",
            "scripts/render_ad_project_contact_sheet.py",
            "scripts/self_test_ad_project_workflow.py",
            "scripts/self_test_run_ad_workflow.py",
        ],
        "phrases": ["ttgstudio.json", "contact sheet", "build_ad_project"],
    },
    {
        "claim": "Canvas interaction has math/controller/widget tests",
        "docs": [],
        "code": [
            "src/ttg_canvas_tools.py",
            "src/ttg_canvas_interaction.py",
            "src/ttg_interactive_canvas.py",
            "scripts/self_test_canvas_tools.py",
            "scripts/self_test_canvas_interaction.py",
            "scripts/self_test_interactive_canvas_widget.py",
        ],
        "phrases": ["ResizeHandle", "DragMode", "InteractiveCanvas"],
    },
    {
        "claim": "Banana Level is deterministic first",
        "docs": ["docs/BANANA_LEVEL.md"],
        "code": ["src/ttg_banana_level.py", "src/ttg_banana_actions.py", "scripts/self_test_banana_level.py"],
        "phrases": ["Make It Pop", "make_it_pop", "deterministic"],
    },
    {
        "claim": "Hunter image worker is a worker bridge, not external-provider dependency",
        "docs": ["docs/IMAGE_INTELLIGENCE_WORKER.md"],
        "code": ["src/ttg_image_intelligence.py", "src/ttg_hunter_image_bridge.py", "scripts/self_test_image_intelligence.py"],
        "phrases": ["Hunter", "worker", "optional", "background_remover_adapter"],
    },
]


def read_all(paths: list[str]) -> str:
    chunks: list[str] = []
    for rel in paths:
        path = ROOT / rel
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def main() -> int:
    failures: list[str] = []
    print("TTG claims-vs-implementation gate")
    print("=================================")
    for claim in CLAIMS:
        missing_files = [rel for rel in [*claim["docs"], *claim["code"]] if not (ROOT / rel).exists()]
        text = read_all([*claim["docs"], *claim["code"]])
        missing_phrases = [phrase for phrase in claim["phrases"] if phrase not in text]
        print(f"- {claim['claim']}")
        if missing_files or missing_phrases:
            failures.append(claim["claim"])
            for rel in missing_files:
                print(f"  missing file: {rel}")
            for phrase in missing_phrases:
                print(f"  missing phrase/evidence: {phrase}")
    if failures:
        print("\nClaims gate failed:")
        for claim in failures:
            print(f"- {claim}")
        return 1
    print("Claims gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
