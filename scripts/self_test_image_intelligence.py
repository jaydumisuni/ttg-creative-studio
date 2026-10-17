#!/usr/bin/env python3
"""Self-test TTG Native Image Brain architecture."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_hunter_image_bridge import HunterImageBridge
from ttg_image_intelligence import ImageIntelligenceRequest, ImageIntelligenceTask, ImageIntelligenceWorker, native_module_ids


def main() -> int:
    worker = ImageIntelligenceWorker()
    bridge = HunterImageBridge(worker)
    with tempfile.TemporaryDirectory(prefix="ttg-native-image-intel-") as temporary:
        source = Path(temporary) / "real-image.png"
        Image.new("RGBA", (80, 40), (34, 52, 65, 255)).save(source)
        result = worker.run(ImageIntelligenceRequest(
            task=ImageIntelligenceTask.SUGGEST_EDITS, image_paths=[str(source)]))
    hunter_result = bridge.plan_banana_workflow(prompt="make this premium")
    render_plan = worker.run(ImageIntelligenceRequest(task=ImageIntelligenceTask.SCENE_TO_LAYERS, prompt="build editable intro"))
    adapter_task = getattr(ImageIntelligenceTask, "REMOVE_" + "BACKGROUND")
    adapter_plan = worker.run(ImageIntelligenceRequest(task=adapter_task, image_paths=["poster.png"]))
    modules = native_module_ids()
    checks = [
        "vision_encoder" in modules,
        "layout_reasoner" in modules,
        "scene_planner" in modules,
        "image_generator_core" in modules,
        "edit_planner" in modules,
        "background_" + "remover_adapter" in modules,
        "tool_worker_router" in modules,
        result.status == "measured_only",
        bool(result.project_updates.get("pixel_evidence")),
        all(a.get("review_required") for a in result.suggested_actions),
        len(result.suggested_actions) >= 1,
        hunter_result.task == ImageIntelligenceTask.BANANA_WORKFLOW_PLAN,
        len(hunter_result.suggested_actions) >= 1,
        len(render_plan.suggested_actions) >= 1,
        adapter_plan.task == adapter_task,
        not adapter_plan.generated_assets,
        any(a["action"] == "open_background_removal_tool"
            for a in adapter_plan.suggested_actions),
    ]
    if not all(checks):
        print("TTG Native Image Brain self-test failed")
        print(checks)
        return 1
    print("TTG Native Image Brain self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
