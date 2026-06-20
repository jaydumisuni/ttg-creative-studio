#!/usr/bin/env python3
"""Image Intelligence Worker architecture for TTG Creative Studio.

This layer is optional and provider-based. The editor must work without it, but
Hunter can later call this worker to understand images, suggest edits, generate
assets, and drive Banana Level workflows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
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


@dataclass(frozen=True)
class ImageProviderSpec:
    id: str
    name: str
    kind: str
    role: str
    optional: bool = True
    notes: str = ""


PROVIDERS = (
    ImageProviderSpec(
        "native_multimodal_transformer",
        "Native Multimodal Transformer",
        "local_or_cloud",
        "Image understanding, layout reasoning, object/style analysis and edit planning.",
        True,
        "Future provider. Can be local, private, or cloud depending on hardware and model availability.",
    ),
    ImageProviderSpec(
        "dalle_3_style_provider",
        "DALL-E 3 compatible provider",
        "cloud_generation",
        "Prompt-to-image generation and concept asset creation.",
        True,
        "Provider interface only. No hard dependency in the core editor.",
    ),
    ImageProviderSpec(
        "chatgpt_images_2_style_provider",
        "ChatGPT Images 2.0 style provider",
        "cloud_generation_editing",
        "Image generation, image editing and creative variation workflows.",
        True,
        "Future-facing provider slot so the app can adapt without redesigning the architecture.",
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
    provider_id: str
    status: str
    message: str
    suggested_actions: list[dict[str, Any]] = field(default_factory=list)
    generated_assets: list[str] = field(default_factory=list)
    project_updates: dict[str, Any] = field(default_factory=dict)


class ImageIntelligenceWorker:
    """Provider-neutral worker facade used by Hunter and Banana Level later."""

    def __init__(self, provider_id: str = "offline_stub") -> None:
        self.provider_id = provider_id

    def run(self, request: ImageIntelligenceRequest) -> ImageIntelligenceResult:
        # Offline deterministic stub. Real providers plug in later.
        actions: list[dict[str, Any]] = []
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
        return ImageIntelligenceResult(
            task=request.task,
            provider_id=self.provider_id,
            status="stubbed",
            message="Image Intelligence Worker is wired as architecture. Real providers are optional future plugins.",
            suggested_actions=actions,
        )


def provider_ids() -> list[str]:
    return [provider.id for provider in PROVIDERS]
