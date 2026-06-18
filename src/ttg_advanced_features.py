#!/usr/bin/env python3
"""Advanced Mode feature registry for TTG Creative Studio."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdvancedFeature:
    id: str
    name: str
    group: str
    status: str
    description: str


ADVANCED_FEATURES = [
    AdvancedFeature("layer_groups", "Layer Groups", "Layers", "planned", "Group/ungroup layers and control visibility/lock state."),
    AdvancedFeature("resize_handles", "Resize Handles", "Canvas", "planned", "Interactive corner/edge handles for resizing selected layers."),
    AdvancedFeature("rotate_handles", "Rotate Handles", "Canvas", "planned", "Interactive rotation handle for selected layers."),
    AdvancedFeature("snap_guides", "Snap Guides", "Canvas", "partial", "Grid snapping exists; visual guides and ruler snapping are needed."),
    AdvancedFeature("blend_modes", "Blend Modes", "Effects", "planned", "Normal, screen, multiply, overlay, add, soft light."),
    AdvancedFeature("neon_glow", "Neon Glow", "Effects", "partial", "Basic glow exists; needs adjustable multi-pass glow."),
    AdvancedFeature("stroke_shadow", "Stroke & Shadow", "Effects", "partial", "Basic text stroke/shadow exists; needs UI controls and presets."),
    AdvancedFeature("bevel_extrude", "Bevel & Extrude", "Effects", "partial", "2.5D extrusion exists; needs proper wordmark preset and controls."),
    AdvancedFeature("reflection", "Reflection", "Effects", "planned", "Floor/reflection pass for premium product/intro renders."),
    AdvancedFeature("gradient_text", "Gradient Text", "Text", "planned", "Gradient fills, chrome materials and neon materials."),
    AdvancedFeature("font_browser", "Font Browser", "Text", "planned", "Font selection and recently used fonts."),
    AdvancedFeature("timeline_keyframes", "Editable Keyframes", "Timeline", "partial", "Keyframe list exists; drag/edit dots needed."),
    AdvancedFeature("easing_editor", "Easing Editor", "Timeline", "planned", "Ease presets and bezier-style control."),
    AdvancedFeature("asset_browser", "Asset Browser", "Assets", "planned", "Brand kit, logos, icons, overlays, backgrounds and sounds."),
    AdvancedFeature("template_browser", "Template Browser", "Templates", "planned", "Visual templates for intros, thumbnails, banners and diagrams."),
    AdvancedFeature("cinematic_intro", "Cinematic Intro Engine", "Render", "partial", "2.5D renderer exists; reference-level result still required."),
    AdvancedFeature("video_preview", "Video Preview", "Render", "planned", "Timeline playback preview inside the app."),
    AdvancedFeature("youtube_export", "YouTube Export Preset", "Export", "planned", "Intro/video presets with fps, resolution and file naming."),
]


def features_by_group() -> dict[str, list[AdvancedFeature]]:
    groups: dict[str, list[AdvancedFeature]] = {}
    for feature in ADVANCED_FEATURES:
        groups.setdefault(feature.group, []).append(feature)
    return groups
