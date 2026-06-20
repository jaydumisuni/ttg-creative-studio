#!/usr/bin/env python3
"""Tool registry for TTG Creative Studio.

Every visible tool should map back to the combined product target so the app does
not become a random pile of buttons.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSpec:
    id: str
    label: str
    mode: str
    target: str
    status: str
    description: str


TOOLS = (
    ToolSpec("select_move", "Select / Move", "advanced", "photoshop_power", "planned", "Click, select and drag layers on the canvas."),
    ToolSpec("resize_rotate", "Resize / Rotate", "advanced", "photoshop_power", "planned", "Handles for scaling and rotating selected layers."),
    ToolSpec("properties_editor", "Properties Editor", "advanced", "photoshop_power", "partial", "Editable fields for position, size, color, opacity and effects."),
    ToolSpec("templates", "Templates", "easy", "canva_simplicity", "partial", "Guided starting points and brand-ready layouts."),
    ToolSpec("asset_browser", "Asset Browser", "easy", "canva_simplicity", "partial", "Logo, image, background and template assets."),
    ToolSpec("preset_picker", "Preset Picker", "easy", "canva_simplicity", "wired", "One-click presets for text, scene, motion and export."),
    ToolSpec("background_remover", "Background Remover", "advanced", "photoshop_power", "partial", "Cutout tool integrated into Creative Studio."),
    ToolSpec("timeline", "Timeline", "motion", "filmora_motion", "partial", "Tracks, timing and keyframes for motion/video."),
    ToolSpec("playback_preview", "Playback Preview", "motion", "filmora_motion", "partial", "Preview motion after still frame is approved."),
    ToolSpec("video_export", "Video Export", "motion", "filmora_motion", "gated", "MP4 export through optional Video Export Pack."),
)


def tools_by_mode() -> dict[str, list[ToolSpec]]:
    groups: dict[str, list[ToolSpec]] = {}
    for tool in TOOLS:
        groups.setdefault(tool.mode, []).append(tool)
    return groups


def status_counts() -> dict[str, int]:
    counts: dict[str, int] = {}
    for tool in TOOLS:
        counts[tool.status] = counts.get(tool.status, 0) + 1
    return counts
