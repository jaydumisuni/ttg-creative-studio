#!/usr/bin/env python3
"""Advanced Mode preset catalog for TTG Creative Studio.

These presets define the kind of controls Photoshop/Canva/Filmora users expect:
text materials, glow stacks, scene looks, motion presets and export presets. The
UI can expose these progressively without hard-coding every button.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    group: str
    description: str
    properties: dict


TEXT_MATERIAL_PRESETS = [
    Preset("neon_chrome", "Neon Chrome", "Text Material", "Purple/cyan gradient with glow, stroke and extrusion.", {"gradient": True, "gradient_start": "#BC13FE", "gradient_end": "#00E5FF", "glow": True, "glow_color": "#00E5FF", "glow_blur": 14, "stroke_width": 4, "stroke_fill": "#120026", "extrude_px": 24, "reflection": True}),
    Preset("glass_white", "Glass White", "Text Material", "Clean white glass text with soft blue glow.", {"color": "#F7FAFF", "glow": True, "glow_color": "#9FD8FF", "glow_blur": 8, "stroke_width": 1, "stroke_fill": "#18305F", "reflection": True}),
    Preset("deep_purple_3d", "Deep Purple 3D", "Text Material", "Darker 3D purple face with strong extrusion.", {"color": "#BC13FE", "glow": True, "glow_color": "#BC13FE", "glow_blur": 12, "stroke_width": 3, "stroke_fill": "#080014", "extrude_px": 34, "extrude_color": "#170033"}),
]

EFFECT_STACK_PRESETS = [
    Preset("premium_wordmark", "Premium Wordmark Stack", "Effects", "Full wordmark polish stack.", {"use": ["gradient", "stroke", "shadow", "glow", "extrude", "reflection"]}),
    Preset("glass_card", "Glass Card Stack", "Effects", "Glass panel with outline, blur-look fill, glow and reflection.", {"fill": "#07132F80", "outline": "#00E5FF", "radius": 28, "glow": True, "reflection": True}),
    Preset("cyber_floor", "Cyber Floor", "Scene", "Perspective grid with foreground sweep lines.", {"floor": True, "perspective": True, "sweep": True}),
]

MOTION_PRESETS = [
    Preset("dark_start_reveal", "Dark Start Reveal", "Motion", "Start black, then light beams and logo come alive.", {"blackout_start": 0.08, "brightness_ramp": True, "scanline": True}),
    Preset("side_light_wipe", "Side Light Wipe", "Motion", "Purple/cyan side panels sweep into frame.", {"side_wipes": True, "ease": "ease_out_cubic"}),
    Preset("final_glow_lock", "Final Glow Lock", "Motion", "Final bloom pulse and clean lockup.", {"glow_pulse": True, "settle": True}),
]

EXPORT_PRESETS = [
    Preset("youtube_intro_1080p", "YouTube Intro 1080p", "Export", "1920x1080, 30fps, H.264 proof target.", {"width": 1920, "height": 1080, "fps": 30, "codec": "h264"}),
    Preset("social_preview_gif", "Social Preview GIF", "Export", "Small animated preview for review.", {"width": 640, "height": 360, "fps": 14, "format": "gif"}),
]

ALL_PRESETS = TEXT_MATERIAL_PRESETS + EFFECT_STACK_PRESETS + MOTION_PRESETS + EXPORT_PRESETS


def presets_by_group() -> dict[str, list[Preset]]:
    groups: dict[str, list[Preset]] = {}
    for preset in ALL_PRESETS:
        groups.setdefault(preset.group, []).append(preset)
    return groups


def find_preset(preset_id: str) -> Preset:
    for preset in ALL_PRESETS:
        if preset.id == preset_id:
            return preset
    raise KeyError(preset_id)
