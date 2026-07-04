#!/usr/bin/env python3
"""TTG Native Image Brain architecture for Creative Studio and Hunter.

This is not a set of reserved external provider slots. TTG builds its own native
multimodal image engine and borrows the best architectural ideas: image
understanding, generation planning, image editing, scene-to-layer conversion,
layout critique and tool-worker execution.

The editor must still work without the brain. The brain becomes Hunter's image
worker and Creative Studio's Banana Level intelligence layer later.
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
        "Understands image content, composition, objects, text regions, colors and style.",
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
        "Creates native assets, backgrounds, concepts and variants when generation is needed.",
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
    """TTG-native worker facade used by Hunter and Banana Level later."""

    def __init__(self, engine_id: str = "ttg_native_image_brain_stub") -> None:
        self.engine_id = engine_id

    def run(self, request: ImageIntelligenceRequest) -> ImageIntelligenceResult:
        actions: list[dict[str, Any]] = []
        modules = ["vision_encoder", "layout_reasoner", "scene_planner", "tool_worker_router"]
        generated_assets: list[str] = []
        project_updates: dict[str, Any] = {}
        if request.task == ImageIntelligenceTask.SUGGEST_EDITS:
            actions.extend([
                {"action": "apply_banana_workflow", "workflow": "make_it_pop"},
                {"action": "check_alignment", "target": "all_layers"},
                {"action": "suggest_export", "preset": "youtube_intro_1080p"},
            ])
        elif request.task == ImageIntelligenceTask.BANANA_WORKFLOW_PLAN:
            actions.extend([
                {"action": "apply_banana_workflow", "workflow": "brand_everything"},
                {"action": "apply_banana_workflow", "workflow": "make_it_pop"},
            ])
        elif request.task == ImageIntelligenceTask.UNDERSTAND_IMAGE:
            actions.append({"action": "describe_layers", "confidence": "stub"})
        elif request.task == ImageIntelligenceTask.REMOVE_BACKGROUND:
            modules.extend(["edit_planner", "background_remover_adapter"])
            actions.append({"action": "remove_background", "mode": "editable_mask", "review_required": True})
            for image_path in request.image_paths:
                generated_assets.append(str(Path(image_path).with_suffix(".bg_removed.png")))
            project_updates["background_removal"] = {
                "mode": "adapter",
                "source_images": list(request.image_paths),
                "output_assets": generated_assets,
                "editable_mask": True,
            }
        elif request.task in {ImageIntelligenceTask.RENDER_PLAN, ImageIntelligenceTask.EDIT_PLAN, ImageIntelligenceTask.SCENE_TO_LAYERS}:
            modules.extend(["image_generator_core", "edit_planner"])
            actions.append({"action": "create_editable_scene_plan", "format": "ttg_project_layers"})
        return ImageIntelligenceResult(
            task=request.task,
            engine_id=self.engine_id,
            status="stubbed_native_architecture",
            message="TTG Native Image Brain architecture is wired. External slots removed; this is our own engine path.",
            suggested_actions=actions,
            generated_assets=generated_assets,
            project_updates=project_updates,
            native_modules_used=modules,
        )


def native_module_ids() -> list[str]:
    return [module.id for module in NATIVE_MODULES]
