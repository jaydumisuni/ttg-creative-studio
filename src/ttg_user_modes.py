#!/usr/bin/env python3
"""User-friendly mode definitions for TTG Creative Studio."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserMode:
    id: str
    name: str
    description: str
    visible_panels: tuple[str, ...]
    primary_actions: tuple[str, ...]


MODES = (
    UserMode(
        "easy",
        "Easy Mode",
        "Canva-like guided creation: templates, presets, brand assets and quick export.",
        ("Templates", "Assets", "Properties", "Preview"),
        ("choose_template", "apply_preset", "replace_logo", "edit_text", "quick_export"),
    ),
    UserMode(
        "advanced",
        "Advanced Mode",
        "Photoshop-like layer control: canvas editing, effects, masks and detailed properties.",
        ("Layers", "Canvas", "Properties", "Advanced", "Assets"),
        ("select_layer", "drag_layer", "resize_layer", "edit_properties", "apply_effect", "mask_background"),
    ),
    UserMode(
        "motion",
        "Motion Mode",
        "Filmora-like video flow: timeline, keyframes, playback and export packs.",
        ("Timeline", "Canvas", "Playback", "Properties", "Packs"),
        ("add_keyframe", "preview_motion", "export_frames", "export_mp4", "install_video_pack"),
    ),
)


def mode_ids() -> list[str]:
    return [mode.id for mode in MODES]


def find_mode(mode_id: str) -> UserMode:
    for mode in MODES:
        if mode.id == mode_id:
            return mode
    raise KeyError(mode_id)
