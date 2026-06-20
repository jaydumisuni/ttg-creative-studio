#!/usr/bin/env python3
"""Product target map for TTG Creative Studio.

The product is not trying to copy one app. The target is a combined standard:
Photoshop power, Canva simplicity and Filmora-style motion/video flow.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductTarget:
    id: str
    name: str
    promise: str
    required_capabilities: tuple[str, ...]


TARGETS = (
    ProductTarget(
        "photoshop_power",
        "Photoshop Power",
        "Precise layered editing, effects, masks, text polish and pixel-level control.",
        (
            "direct_canvas_selection",
            "drag_resize_rotate_handles",
            "layer_stack",
            "properties_editor",
            "mask_and_background_tools",
            "advanced_text_effects",
            "blend_shadow_glow_stroke_gradient",
        ),
    ),
    ProductTarget(
        "canva_simplicity",
        "Canva Simplicity",
        "Templates, presets and guided workflows that make good results easy.",
        (
            "template_browser",
            "brand_kit",
            "one_click_presets",
            "asset_browser",
            "easy_mode",
            "quick_export",
            "safe_defaults",
        ),
    ),
    ProductTarget(
        "filmora_motion",
        "Filmora Motion",
        "Timeline, keyframes, playback preview and clean video export flow.",
        (
            "timeline_tracks",
            "keyframe_dots",
            "playback_preview",
            "motion_presets",
            "frame_export",
            "mp4_export_pack",
            "audio_markers",
        ),
    ),
)


def capability_index() -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for target in TARGETS:
        for capability in target.required_capabilities:
            index.setdefault(capability, []).append(target.id)
    return index


def target_names() -> list[str]:
    return [target.name for target in TARGETS]
