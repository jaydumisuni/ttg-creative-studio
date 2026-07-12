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
OUTPUTS = ROOT / "outputs"
LOG_PATH = OUTPUTS / "REVIEW_GATE_LOG.txt"
COMMANDS = [
    ["scripts/self_check_visual_pipeline.py"],
    ["scripts/review_compile_gate.py"],
    ["scripts/building_standard_report.py"],
    ["scripts/benchmark_targets_report.py"],
    ["scripts/review_claims_gate.py"],
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
    ["scripts/build_benchmark_gap_report.py"],
    ["scripts/build_release_decision.py"],
]


def emit(text: str, log: list[str]) -> None:
    print(text)
    log.append(text)


def run_command(script: str, log: list[str]) -> int:
    emit(f"\n=== {script} ===", log)
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    result = subprocess.run(
        [sys.executable, script],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
        errors="replace",
    )
    if result.stdout:
        emit(result.stdout.rstrip(), log)
    if result.stderr:
        emit("--- stderr ---", log)
        emit(result.stderr.rstrip(), log)
    emit(f"Exit code: {result.returncode}", log)
    return result.returncode


def write_log(log: list[str]) -> None:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("\n".join(log) + "\n", encoding="utf-8")


def main() -> int:
    log: list[str] = []
    emit("THETECHGUY Creative Studio review gate", log)
    emit("======================================", log)
    failed: list[str] = []
    for command in COMMANDS:
        code = run_command(command[0], log)
        if code != 0:
            failed.append(command[0])
            break
    if failed:
        emit("\nReview gate failed:", log)
        for script in failed:
            emit(f"- {script}", log)
        write_log(log)
        return 1
    emit("\nReview gate passed", log)
    write_log(log)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
