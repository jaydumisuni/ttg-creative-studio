#!/usr/bin/env python3
"""Fast structural self-check for the visual proof and product direction pipeline."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "src/ttg_reference_still_renderer.py",
    "src/ttg_reference_motion_renderer.py",
    "src/ttg_advanced_presets.py",
    "src/ttg_preset_actions.py",
    "src/ttg_workspace_preset_bridge.py",
    "src/ttg_property_schema.py",
    "src/ttg_canvas_tools.py",
    "src/ttg_canvas_interaction.py",
    "src/ttg_interactive_canvas.py",
    "src/ttg_asset_package.py",
    "src/ttg_product_targets.py",
    "src/ttg_user_modes.py",
    "src/ttg_tool_registry.py",
    "src/ttg_banana_level.py",
    "src/ttg_banana_actions.py",
    "src/ttg_image_intelligence.py",
    "src/ttg_hunter_image_bridge.py",
    "scripts/check_property_schema.py",
    "scripts/build_ad_project_from_assets.py",
    "scripts/run_ad_workflow.py",
    "scripts/building_standard_report.py",
    "scripts/review_compile_gate.py",
    "scripts/review_claims_gate.py",
    "scripts/review_gate_all.py",
    "scripts/self_test_asset_package.py",
    "scripts/self_test_ad_project_workflow.py",
    "scripts/self_test_run_ad_workflow.py",
    "scripts/self_test_canvas_tools.py",
    "scripts/self_test_canvas_interaction.py",
    "scripts/self_test_interactive_canvas_widget.py",
    "scripts/self_test_presets.py",
    "scripts/self_test_workspace_preset_bridge.py",
    "scripts/self_test_app_wiring.py",
    "scripts/self_test_ui_offscreen.py",
    "scripts/self_test_banana_level.py",
    "scripts/self_test_image_intelligence.py",
    "scripts/product_direction_report.py",
    "scripts/generate_visual_proof_package.py",
    "scripts/build_motion_contact_sheet.py",
    "scripts/build_motion_gif_preview.py",
    "scripts/build_artifact_index.py",
    "scripts/build_review_summary.py",
    "scripts/build_preset_report.py",
    "scripts/proof_status.py",
    "scripts/check_video_gate.py",
    "scripts/build_video_proof.py",
    "docs/THETECHGUY_BUILDING_STANDARD.md",
    "docs/PRODUCT_STANDARD.md",
    "docs/UI_LAST_RULE.md",
    "docs/BANANA_LEVEL.md",
    "docs/IMAGE_INTELLIGENCE_WORKER.md",
    "docs/VISUAL_APPROVAL_GATE.md",
    "docs/VIDEO_PROOF_STAGE.md",
    "docs/NO_RELEASE_UNTIL.md",
    "docs/ADVANCED_MODE_PRESETS.md",
    "packs/video-export-pack.json",
    ".github/workflows/reference-preview.yml",
]


def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).exists()]
    print("TTG product/visual pipeline structural self-check")
    print("================================================")
    if missing:
        print("Missing files:")
        for path in missing:
            print(f"  - {path}")
        return 1
    print(f"All required files present: {len(REQUIRED)}")
    print("Target: THETECHGUY Building Standard + engine/workflow/proof first, UI last.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
