#!/usr/bin/env python3
"""Run the THETECHGUY Creative Studio review gate.

This is the single proof command for the current engine/workflow stage. It does
not replace clean-clone proof, but it gives CI and local review one command that
runs the intended safety net in order.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = [
    ["scripts/self_check_visual_pipeline.py"],
    ["scripts/review_compile_gate.py"],
    ["scripts/building_standard_report.py"],
    ["scripts/product_direction_report.py"],
    ["scripts/check_property_schema.py"],
    ["scripts/self_test_asset_package.py"],
    ["scripts/self_test_ad_project_workflow.py"],
    ["scripts/self_test_run_ad_workflow.py"],
    ["scripts/self_test_canvas_tools.py"],
    ["scripts/self_test_canvas_interaction.py"],
    ["scripts/self_test_interactive_canvas_widget.py"],
    ["scripts/self_test_banana_level.py"],
    ["scripts/self_test_image_intelligence.py"],
    ["scripts/self_test_presets.py"],
    ["scripts/self_test_workspace_preset_bridge.py"],
    ["scripts/self_test_app_wiring.py"],
    ["scripts/self_test_ui_offscreen.py"],
    ["scripts/generate_visual_proof_package.py"],
]


def run_command(script: str) -> int:
    print("\n===", script, "===")
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    result = subprocess.run([sys.executable, script], cwd=ROOT, env=env, check=False)
    return result.returncode


def main() -> int:
    print("THETECHGUY Creative Studio review gate")
    print("======================================")
    failed: list[str] = []
    for command in COMMANDS:
        code = run_command(command[0])
        if code != 0:
            failed.append(command[0])
            break
    if failed:
        print("\nReview gate failed:")
        for script in failed:
            print(f"- {script}")
        return 1
    print("\nReview gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
