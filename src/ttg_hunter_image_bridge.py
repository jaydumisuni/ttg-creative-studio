#!/usr/bin/env python3
"""Hunter bridge for TTG Image Intelligence Worker.

Hunter should call this as a worker, not replace the editor. The worker can
understand images, plan edits and suggest deterministic TTG actions.
"""

from __future__ import annotations

from ttg_image_intelligence import ImageIntelligenceRequest, ImageIntelligenceTask, ImageIntelligenceWorker


class HunterImageBridge:
    def __init__(self, worker: ImageIntelligenceWorker | None = None) -> None:
        self.worker = worker or ImageIntelligenceWorker()

    def understand_image(self, image_path: str, prompt: str = ""):
        return self.worker.run(ImageIntelligenceRequest(
            task=ImageIntelligenceTask.UNDERSTAND_IMAGE,
            prompt=prompt,
            image_paths=[image_path],
        ))

    def suggest_edits(self, image_path: str, prompt: str = ""):
        return self.worker.run(ImageIntelligenceRequest(
            task=ImageIntelligenceTask.SUGGEST_EDITS,
            prompt=prompt,
            image_paths=[image_path],
        ))

    def plan_banana_workflow(self, project_path: str | None = None, prompt: str = ""):
        return self.worker.run(ImageIntelligenceRequest(
            task=ImageIntelligenceTask.BANANA_WORKFLOW_PLAN,
            prompt=prompt,
            project_path=project_path,
        ))
