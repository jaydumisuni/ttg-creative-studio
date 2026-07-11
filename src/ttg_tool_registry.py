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
    ToolSpec("select_move", "Select / Move", "advanced", "photoshop_power", "engine_done", "Canvas math, interaction controller and widget smoke test exist."),
    ToolSpec("resize_rotate", "Resize / Rotate", "advanced", "photoshop_power", "engine_done", "Resize and rotate handle paths exist at controller/widget level."),
    ToolSpec("properties_editor", "Properties Editor", "advanced", "photoshop_power", "engine_done", "Property engine edits layer name, transform, opacity, properties and effects."),
    ToolSpec("templates", "Templates", "easy", "canva_simplicity", "workflow_done", "Template/preset workflow exists; final browser UI remains UI-last."),
    ToolSpec("asset_browser", "Asset Browser", "easy", "canva_simplicity", "engine_done", "Folder/ZIP asset import is implemented and tested."),
    ToolSpec("preset_picker", "Preset Picker", "easy", "canva_simplicity", "wired", "One-click presets for text, scene, motion and export."),
    ToolSpec("background_remover", "Background Adapter", "advanced", "photoshop_power", "adapter_done", "Image worker adapter maps cutout/background cleanup into Creative Studio action planning."),
    ToolSpec("timeline", "Timeline", "motion", "filmora_motion", "engine_done", "Layer timing, keyframes, clip listing and interpolation exist in the engine."),
    ToolSpec("playback_preview", "Playback Preview", "motion", "filmora_motion", "proof_done", "GIF/contact-sheet motion proof exists before full UI playback."),
    ToolSpec("video_export", "Video Export", "motion", "filmora_motion", "gated", "MP4 export is gated behind review and optional Video Export Pack/FFmpeg detection."),
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
