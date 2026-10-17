#!/usr/bin/env python3
"""Evidence-grounded visual analysis for standalone TTG Creative Studio.

Native pixel measurements work offline. Optional semantic image interpretation
requires an actually installed local vision-language model. Render planning and
generation remain separate: this module never claims to render an asset, infer
hidden visual details, or perform an edit without an approved tool invocation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ImageIntelligenceTask(str, Enum):
    UNDERSTAND_IMAGE = "understand_image"
    SUGGEST_EDITS = "suggest_edits"
    GENERATE_ASSET = "generate_asset"
    GENERATE_VARIANTS = "generate_variants"
    IMAGE_TO_TEMPLATE = "image_to_template"
    PROMPT_TO_SCENE = "prompt_to_scene"
    SCENE_TO_LAYERS = "scene_to_layers"
    BANANA_WORKFLOW_PLAN = "banana_workflow_plan"
    RENDER_PLAN = "render_plan"
    EDIT_PLAN = "edit_plan"
    REMOVE_BACKGROUND = "remove_background"


@dataclass(frozen=True)
class NativeImageBrainModule:
    id: str
    name: str
    role: str
    required: bool = True


NATIVE_MODULES = (
    NativeImageBrainModule(
        "vision_encoder",
        "Vision Encoder",
        "Measures observed pixels; optional installed VLM interprets visible content.",
    ),
    NativeImageBrainModule(
        "layout_reasoner",
        "Layout Reasoner",
        "Judges hierarchy, alignment, spacing, balance and brand fit.",
    ),
    NativeImageBrainModule(
        "scene_planner",
        "Scene Planner",
        "Turns prompts or image understanding into editable TTG project/layer plans.",
    ),
    NativeImageBrainModule(
        "image_generator_core",
        "Image Generator Core",
        "Generation is implemented separately by the qualified ComfyUI editing interface.",
        required=False,
    ),
    NativeImageBrainModule(
        "edit_planner",
        "Edit Planner",
        "Plans safe image edits that can map back to layers, masks, effects and Banana workflows.",
    ),
    NativeImageBrainModule(
        "background_remover_adapter",
        "Background Remover Adapter",
        "Wraps background removal as an editable Creative Studio action instead of a separate tool.",
        required=False,
    ),
    NativeImageBrainModule(
        "tool_worker_router",
        "Tool Worker Router",
        "Routes plans into deterministic Creative Studio actions instead of hiding everything in a flat bitmap.",
    ),
)


@dataclass
class ImageIntelligenceRequest:
    task: ImageIntelligenceTask
    prompt: str = ""
    image_paths: list[str] = field(default_factory=list)
    project_path: str | None = None
    brand_context: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageIntelligenceResult:
    task: ImageIntelligenceTask
    engine_id: str
    status: str
    message: str
    suggested_actions: list[dict[str, Any]] = field(default_factory=list)
    generated_assets: list[str] = field(default_factory=list)
    project_updates: dict[str, Any] = field(default_factory=dict)
    native_modules_used: list[str] = field(default_factory=list)


class ImageIntelligenceWorker:
    """Measured image evidence, optional installed local VLM, review-only edits."""

    def __init__(self, engine_id: str = "ttg_image_intelligence_v1",
                 vision_model: str | None = None,
                 vision_endpoint: str = "http://127.0.0.1:11434") -> None:
        self.engine_id = engine_id
        self.vision_model = vision_model
        self.vision_endpoint = vision_endpoint

    def run(self, request: ImageIntelligenceRequest) -> ImageIntelligenceResult:
        from ttg_visual_understanding import (
            LocalOllamaVision, measure_image, suggest_adjustments,
        )

        modules = ["vision_encoder", "layout_reasoner", "tool_worker_router"]
        project_updates: dict[str, Any] = {}
        actions: list[dict[str, Any]] = []
        messages: list[str] = []
        status = "review_only"

        if request.task in {ImageIntelligenceTask.UNDERSTAND_IMAGE,
                            ImageIntelligenceTask.SUGGEST_EDITS}:
            if not request.image_paths:
                return ImageIntelligenceResult(
                    request.task, self.engine_id, "missing_image",
                    "Select a real image for visual analysis.", native_modules_used=modules
                )
            measurements = [measure_image(path) for path in request.image_paths[:4]]
            project_updates["pixel_evidence"] = measurements
            if request.task == ImageIntelligenceTask.SUGGEST_EDITS:
                modules.append("edit_planner")
                for metrics in measurements:
                    for item in suggest_adjustments(metrics):
                        actions.append({**item, "source_sha256": metrics["source_sha256"]})
            messages.append("Measured actual image pixels and colors; object recognition requires an installed vision-language model.")
            status = "measured_only"
            if self.vision_model:
                try:
                    model = LocalOllamaVision(self.vision_endpoint)
                    descriptions = [
                        model.describe(item["source"], self.vision_model, request.prompt)
                        for item in measurements
                    ]
                    project_updates["visual_descriptions"] = descriptions
                    project_updates["vision_model"] = self.vision_model
                    modules.append("semantic_vision_model")
                    status = "model_vision_review_required"
                    messages.append("Actual locally installed vision model returned a visual interpretation; human review required.")
                except (OSError, ValueError, TimeoutError) as exc:
                    project_updates["model_unavailable"] = str(exc)
                    messages.append("Vision-model interpretation unavailable; only measured pixels are reported.")

        elif request.task == ImageIntelligenceTask.REMOVE_BACKGROUND:
            actions.append({
                "action": "open_background_removal_tool",
                "review_required": True,
                "source_images": list(request.image_paths),
            })
            modules.append("background_remover_adapter")
            messages.append("Background removal requires executing the existing editor tool. No output file has been generated.")

        elif request.task == ImageIntelligenceTask.BANANA_WORKFLOW_PLAN:
            modules.append("edit_planner")
            actions.append({"action": "review_layout_and_effects", "review_required": True})
            messages.append("Workflow planning only; project unchanged.")

        else:
            modules.extend(["scene_planner", "edit_planner"])
            actions.append({
                "action": "review_scene_plan",
                "prompt": request.prompt[:2000],
                "review_required": True,
            })
            messages.append("Scene generation needs a separate qualified image model and explicit editor execution.")

        return ImageIntelligenceResult(
            task=request.task,
            engine_id=self.engine_id,
            status=status,
            message=" ".join(messages),
            suggested_actions=actions,
            generated_assets=[],
            project_updates=project_updates,
            native_modules_used=modules,
        )


def native_module_ids() -> list[str]:
    return [module.id for module in NATIVE_MODULES]
