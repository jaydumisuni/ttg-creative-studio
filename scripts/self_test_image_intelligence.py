#!/usr/bin/env python3
"""Self-test Image Intelligence Worker architecture."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_hunter_image_bridge import HunterImageBridge
from ttg_image_intelligence import ImageIntelligenceRequest, ImageIntelligenceTask, ImageIntelligenceWorker, provider_ids


def main() -> int:
    worker = ImageIntelligenceWorker()
    bridge = HunterImageBridge(worker)
    result = worker.run(ImageIntelligenceRequest(task=ImageIntelligenceTask.SUGGEST_EDITS, image_paths=["example.png"]))
    hunter_result = bridge.plan_banana_workflow(prompt="make this premium")
    checks = [
        "native_multimodal_transformer" in provider_ids(),
        "dalle_3_style_provider" in provider_ids(),
        "chatgpt_images_2_style_provider" in provider_ids(),
        result.status == "stubbed",
        len(result.suggested_actions) >= 1,
        hunter_result.task == ImageIntelligenceTask.BANANA_WORKFLOW_PLAN,
        len(hunter_result.suggested_actions) >= 1,
    ]
    if not all(checks):
        print("Image Intelligence self-test failed")
        print(checks)
        return 1
    print("Image Intelligence self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
