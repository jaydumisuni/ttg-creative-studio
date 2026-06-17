#!/usr/bin/env python3
"""
TTG Creative Studio project schema.

This is the non-AI foundation. Hunter/AI can later create or edit these
project files, but the app must be able to load, edit, preview, and export
them manually first.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Literal
import json
import uuid

LayerType = Literal[
    "image",
    "text",
    "text3d",
    "shape",
    "svg",
    "video",
    "audio",
    "particle",
    "camera",
    "light",
    "diagram_node",
    "connector_line",
    "measurement",
    "group",
]

Easing = Literal[
    "linear",
    "ease_in",
    "ease_out",
    "ease_in_out",
    "ease_out_back",
    "bounce",
]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class CanvasSpec:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    duration: float = 8.0
    background: str = "#050614"


@dataclass
class Keyframe:
    time: float
    value: Any
    easing: Easing = "ease_in_out"


@dataclass
class Transform:
    x: float = 0
    y: float = 0
    z: float = 0
    scale_x: float = 1
    scale_y: float = 1
    scale_z: float = 1
    rotation_x: float = 0
    rotation_y: float = 0
    rotation_z: float = 0
    opacity: float = 1


@dataclass
class Layer:
    id: str
    type: LayerType
    name: str
    visible: bool = True
    locked: bool = False
    transform: Transform = field(default_factory=Transform)
    properties: dict[str, Any] = field(default_factory=dict)
    effects: list[dict[str, Any]] = field(default_factory=list)
    keyframes: dict[str, list[Keyframe]] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)


@dataclass
class Asset:
    id: str
    kind: str
    name: str
    path: str
    sha256: str | None = None
    pack_id: str | None = None
    required: bool = False


@dataclass
class BrandKit:
    id: str = "ttg_default"
    name: str = "THETECHGUY DIGITAL SOLUTIONS"
    website: str = "thetechguyds.com"
    slogan: str = "Fairytale Business — Make a wish, we sort it."
    pillars: list[str] = field(default_factory=lambda: ["SYSTEMS", "TOOLS", "ISP", "WEB"])
    colors: dict[str, str] = field(default_factory=lambda: {
        "black": "#050614",
        "cyan": "#00E5FF",
        "purple": "#BC13FE",
        "white": "#F7FAFF",
    })
    locked_assets: dict[str, str] = field(default_factory=dict)


@dataclass
class TTGProject:
    version: str = "0.1.0"
    project_type: Literal["image", "motion", "diagram", "mixed"] = "motion"
    name: str = "Untitled TTG Project"
    canvas: CanvasSpec = field(default_factory=CanvasSpec)
    brand: BrandKit = field(default_factory=BrandKit)
    assets: list[Asset] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)
    audio_markers: list[dict[str, Any]] = field(default_factory=list)
    export: dict[str, Any] = field(default_factory=lambda: {
        "format": "mp4",
        "quality": "1080p",
        "codec": "h264",
    })

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @staticmethod
    def load(path: str | Path) -> "TTGProject":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        project = TTGProject(
            version=data.get("version", "0.1.0"),
            project_type=data.get("project_type", "motion"),
            name=data.get("name", "Untitled TTG Project"),
        )
        project.canvas = CanvasSpec(**data.get("canvas", {}))
        project.brand = BrandKit(**data.get("brand", {}))
        project.assets = [Asset(**a) for a in data.get("assets", [])]
        project.layers = []
        for raw in data.get("layers", []):
            transform = Transform(**raw.get("transform", {}))
            keyframes = {
                prop: [Keyframe(**kf) for kf in frames]
                for prop, frames in raw.get("keyframes", {}).items()
            }
            project.layers.append(Layer(
                id=raw["id"],
                type=raw["type"],
                name=raw.get("name", raw["id"]),
                visible=raw.get("visible", True),
                locked=raw.get("locked", False),
                transform=transform,
                properties=raw.get("properties", {}),
                effects=raw.get("effects", []),
                keyframes=keyframes,
                children=raw.get("children", []),
            ))
        project.audio_markers = data.get("audio_markers", [])
        project.export = data.get("export", project.export)
        return project


def make_ttg_intro_project() -> TTGProject:
    project = TTGProject(name="TTG Cinematic Intro", project_type="motion")
    project.layers.extend([
        Layer(id="bg_world", type="image", name="Digital world background"),
        Layer(id="particles", type="particle", name="Purple/cyan energy particles"),
        Layer(id="camera", type="camera", name="Cinematic camera"),
        Layer(id="wordmark", type="text3d", name="THETECHGUY 3D wordmark", properties={"text": "THETECHGUY"}),
        Layer(id="subtitle", type="text", name="DIGITAL SOLUTIONS", properties={"text": "DIGITAL SOLUTIONS"}),
        Layer(id="ghost", type="image", name="Official TTG ghost logo", properties={"asset": "ttg_ghost_original", "locked_design": True}),
        Layer(id="systems", type="text3d", name="SYSTEMS panel", properties={"text": "SYSTEMS"}),
        Layer(id="tools", type="text3d", name="TOOLS panel", properties={"text": "TOOLS"}),
        Layer(id="isp", type="text3d", name="ISP panel", properties={"text": "ISP"}),
        Layer(id="web", type="text3d", name="WEB panel", properties={"text": "WEB"}),
        Layer(id="tagline", type="text", name="Tagline", properties={"text": project.brand.slogan}),
        Layer(id="website", type="text", name="Website", properties={"text": project.brand.website}),
    ])
    project.audio_markers.extend([
        {"time": 0.7, "name": "startup bass hit"},
        {"time": 1.4, "name": "letters lock"},
        {"time": 3.0, "name": "ghost reveal"},
        {"time": 4.2, "name": "service panels lock"},
        {"time": 6.4, "name": "final chime"},
    ])
    return project
