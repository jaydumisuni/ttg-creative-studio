"""Bounded OpenTimelineIO (FilmCraft-compatible) exchange.

The Studio .ttgstudio project remains authoritative. Interchange exports
actual media/image timeline clips and timing, not a replacement NLE or a
promise of FilmCraft effects, transitions, multicam or audio DSP equivalence.
Unsupported structures fail closed instead of silently flattening edits.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit, unquote
from urllib.request import url2pathname

from ttg_project_schema import CanvasSpec, Keyframe, Layer, Transform, TTGProject

MAX_OTIO_BYTES = 2 * 1024 * 1024
MAX_TRACKS = 128
MAX_MEDIA_SECONDS = 1800
MEDIA_KINDS = frozenset({"video", "image", "audio"})


def _finite(value: object, name: str, *, min_value: float = 0, max_value: float = MAX_MEDIA_SECONDS) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} requires a numeric time")
    n = float(value)
    if not math.isfinite(n) or n < min_value or n > max_value:
        raise ValueError(f"{name} outside supported range")
    return n


def _rt(seconds: float, fps: int) -> dict:
    return {"OTIO_SCHEMA": "RationalTime.1",
            "value": round(seconds * fps, 6), "rate": float(fps)}


def _tr(start: float, duration: float, fps: int) -> dict:
    return {"OTIO_SCHEMA": "TimeRange.1",
            "start_time": _rt(start, fps), "duration": _rt(duration, fps)}


def _secs(value: dict) -> float:
    if not isinstance(value, dict) or value.get("OTIO_SCHEMA") != "RationalTime.1":
        raise ValueError("OTIO RationalTime.1 is required")
    rate = _finite(value.get("rate"), "OTIO rate", min_value=0.01, max_value=240)
    v = _finite(value.get("value"), "OTIO frame count", max_value=500000)
    return v / rate


def _duration(tr: dict) -> tuple[float, float]:
    if not isinstance(tr, dict) or tr.get("OTIO_SCHEMA") != "TimeRange.1":
        raise ValueError("OTIO TimeRange.1 is required")
    start = _secs(tr.get("start_time"))
    duration = _secs(tr.get("duration"))
    if duration <= 0:
        raise ValueError("OTIO clip duration must be positive")
    return start, duration


def _source_url(source: str, root: Path) -> str:
    path = Path(source)
    if not path.is_absolute():
        path = root / path
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError("Actual media source missing: " + str(path))
    return path.resolve().as_uri()


def _media_url(url: str) -> Path:
    parsed = urlsplit(url)
    if parsed.scheme != "file" or parsed.netloc not in ("", "localhost") or parsed.query or parsed.fragment:
        raise ValueError("OTIO media reference must be a local file URL")
    decoded = unquote(parsed.path)
    if not decoded or "\x00" in decoded:
        raise ValueError("Invalid OTIO media URI")
    path = Path(url2pathname(decoded))
    if not path.is_file():
        raise FileNotFoundError("Referenced OTIO media is missing: " + str(path))
    return path


def _safe_write(dest: Path, payload: bytes) -> None:
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("Interchange never overwrites an existing artifact")
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=f".{dest.stem}-", suffix=".tmp", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as writer:
            writer.write(payload)
            writer.flush()
            os.fsync(writer.fileno())
        if dest.exists() or dest.is_symlink():
            raise FileExistsError("Artifact appeared while staging")
        os.replace(temp, dest)
    finally:
        Path(temp).unlink(missing_ok=True)


def export_otio(project: TTGProject, destination: str | Path,
                *, project_root: str | Path) -> dict:
    """Exchange independent video, still and audio tracks with OTIO .otio.

    Each Studio media layer maps to one independent track, so overlapping clips
    remain overlapping. FilmCraft may expand/rearrange these tracks and uses
    standard OTIO fields for actual time, media URL and track kind.
    """
    dest = Path(destination)
    if dest.suffix.lower() != ".otio":
        raise ValueError("FilmCraft exchange needs a .otio destination")
    width, height, fps = int(project.canvas.width), int(project.canvas.height), int(project.canvas.fps)
    if width * height > 16_000_000 or not 1 <= fps <= 120:
        raise ValueError("Invalid Studio video timeline dimensions or FPS")
    if len(project.layers) > MAX_TRACKS:
        raise ValueError("Timeline exceeds track budget")
    project_duration = _finite(project.canvas.duration, "project duration")
    if project_duration <= 0:
        raise ValueError("Timeline duration must be positive")
    tracks: list[dict] = []
    warnings: list[str] = []
    unsupported: list[str] = []
    for index, layer in enumerate(project.layers):
        if layer.type not in MEDIA_KINDS:
            unsupported.append(layer.id)
            continue
        path = layer.properties.get("path") or layer.properties.get("asset_path")
        if not isinstance(path, str) or not path:
            raise ValueError(f"Layer {layer.id} has no media path")
        target_url = _source_url(path, Path(project_root))
        start = _finite(layer.properties.get("start", 0), "clip start")
        source_in = _finite(layer.properties.get("source_in", 0), "source in")
        if layer.type == "video":
            source_out = _finite(layer.properties.get("source_out", 0), "source out")
            speed = _finite(layer.properties.get("speed", 1), "clip speed", min_value=0.25, max_value=4)
            if speed != 1.0:
                raise ValueError("OTIO retime requires a qualified native timewarp adapter")
            clip_duration = source_out - source_in
        else:
            clip_duration = _finite(layer.properties.get("duration", project_duration - start),
                                    "clip duration")
        if clip_duration <= 0 or start + clip_duration > project_duration + 1e-4:
            raise ValueError("Clip exceeds Studio timeline duration")
        if layer.effects:
            warnings.append(f"{layer.id}: Studio effects stored in metadata, not FilmCraft-equivalent")
        if layer.keyframes:
            warnings.append(f"{layer.id}: Studio keyframes kept in metadata only")
        gap = ([
            {"OTIO_SCHEMA": "Gap.1", "source_range": _tr(0, start, fps),
             "metadata": {}}
        ] if start > 0 else [])
        clip = {
            "OTIO_SCHEMA": "Clip.1",
            "name": layer.name,
            "source_range": _tr(source_in, clip_duration, fps),
            "media_reference": {
                "OTIO_SCHEMA": "ExternalReference.1",
                "target_url": target_url,
                "available_range": None,
                "metadata": {},
            },
            "effects": [],
            "markers": [],
            "enabled": layer.visible,
            "metadata": {"ttg_studio": {
                "original_layer": asdict(layer),
                "layer_id": layer.id, "original_order": index,
            }},
        }
        tracks.append({
            "OTIO_SCHEMA": "Track.1", "name": layer.name,
            "kind": "Audio" if layer.type == "audio" else "Video",
            "children": gap + [clip],
            "effects": [], "markers": [],
            "enabled": True, "metadata": {"ttg_studio": {"layer_id": layer.id}},
        })
    if unsupported:
        warnings.append("Non-media layers kept only in original Studio project: "
                        + ", ".join(unsupported[:30]))
    if not tracks:
        raise ValueError("No media timeline clips for FilmCraft interchange")
    doc = {
        "OTIO_SCHEMA": "Timeline.1",
        "name": project.name,
        "global_start_time": _rt(0, fps),
        "tracks": {
            "OTIO_SCHEMA": "Stack.1", "name": project.name,
            "children": tracks, "effects": [], "markers": [], "metadata": {},
        },
        "metadata": {"ttg_studio": {
            "source": "ttg_studio", "canvas": asdict(project.canvas),
            "nonmedia_layers": unsupported,
            "interchange_version": "1",
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }},
    }
    raw = (json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()
    if len(raw) > MAX_OTIO_BYTES:
        raise ValueError("OTIO exceeds bounded project size")
    _safe_write(dest, raw)
    return {
        "format": "otio", "tracks": len(tracks),
        "output": str(dest), "sha256": hashlib.sha256(raw).hexdigest(),
        "warnings": warnings, "preserved_native_project": True,
    }


def import_otio(source: str | Path, destination: str | Path) -> dict:
    """Read simple OTIO clips into native editable Studio media layers.

    Unknown transitions, effects, nested projects, timewarp, multiple clips per
    track and other features are rejected, never silently removed.
    """
    origin, dest = Path(source), Path(destination)
    if origin.suffix.lower() != ".otio" or not dest.name.endswith(".json"):
        raise ValueError("Expected .otio input and .ttgstudio.json output")
    if not origin.is_file() or origin.stat().st_size > MAX_OTIO_BYTES:
        raise ValueError("Missing or oversized OTIO")
    obj = json.loads(origin.read_text(encoding="utf-8"))
    if not isinstance(obj, dict) or obj.get("OTIO_SCHEMA") != "Timeline.1":
        raise ValueError("OTIO Timeline.1 required")
    stack = obj.get("tracks")
    if not isinstance(stack, dict) or stack.get("OTIO_SCHEMA") != "Stack.1":
        raise ValueError("OTIO Stack.1 required")
    tracks = stack.get("children")
    if not isinstance(tracks, list) or len(tracks) > MAX_TRACKS:
        raise ValueError("OTIO track count exceeds budget")
    canvas_data = obj.get("metadata", {}).get("ttg_studio", {}).get("canvas", {})
    if canvas_data:
        canvas = CanvasSpec(**canvas_data)
    else:
        canvas = CanvasSpec(duration=0.1)
    if canvas.width * canvas.height > 16_000_000 or not 1 <= canvas.fps <= 120:
        raise ValueError("OTIO canvas exceeds size/fps limits")
    project = TTGProject(name=str(obj.get("name") or origin.stem)[:150],
                         project_type="motion", canvas=canvas)
    used: set[str] = set()
    for i, track in enumerate(tracks):
        if not isinstance(track, dict) or track.get("OTIO_SCHEMA") != "Track.1":
            raise ValueError("Nested or unsupported OTIO track")
        if track.get("effects") or track.get("markers") or track.get("enabled") is False:
            raise ValueError("OTIO track effects/markers/mute unsupported")
        children = track.get("children")
        if not isinstance(children, list) or not 1 <= len(children) <= 2:
            raise ValueError("Only one clip per track with optional leading gap")
        start = 0.0
        if children[0].get("OTIO_SCHEMA") == "Gap.1":
            if len(children) != 2:
                raise ValueError("Gap without clip")
            gap_in, start = _duration(children[0].get("source_range"))
            if gap_in:
                raise ValueError("OTIO gap source offset unsupported")
            clip = children[1]
        else:
            if len(children) != 1:
                raise ValueError("Multiple clips per track unsupported")
            clip = children[0]
        if clip.get("OTIO_SCHEMA") not in {"Clip.1", "Clip.2"}:
            raise ValueError("Only OTIO clips are supported")
        if clip.get("effects") or clip.get("markers"):
            raise ValueError("OTIO effects/markers require explicit donor adapter")
        ref = clip.get("media_reference")
        if not isinstance(ref, dict) or ref.get("OTIO_SCHEMA") != "ExternalReference.1":
            raise ValueError("Only actual local external media references supported")
        path = _media_url(ref.get("target_url", ""))
        source_in, duration = _duration(clip.get("source_range"))
        metadata = clip.get("metadata", {}).get("ttg_studio", {})
        original = metadata.get("original_layer")
        if isinstance(original, dict):
            transformed = Transform(**original.get("transform", {}))
            keyframes = {k: [Keyframe(**kf) for kf in values]
                         for k, values in original.get("keyframes", {}).items()}
            layer = Layer(
                id=original.get("id", f"otio_{i:04d}"),
                type=original.get("type", "video"),
                name=str(clip.get("name") or original.get("name") or f"Clip {i}"),
                visible=clip.get("enabled", True),
                locked=original.get("locked", False),
                transform=transformed,
                effects=original.get("effects", []),
                keyframes=keyframes,
                properties=original.get("properties", {}).copy(),
            )
        else:
            media_type = ("audio" if track.get("kind") == "Audio"
                          else "image" if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
                          else "video")
            layer = Layer(id=f"otio_{i:04d}", type=media_type,
                          name=str(clip.get("name") or f"Clip {i}"),
                          visible=clip.get("enabled", True))
        if layer.id in used:
            raise ValueError("Duplicate OTIO layer IDs")
        used.add(layer.id)
        layer.properties["path"] = str(path)
        layer.properties["start"] = start
        if layer.type == "video":
            layer.properties["source_in"] = source_in
            layer.properties["source_out"] = source_in + duration
            layer.properties["speed"] = 1.0
        elif layer.type not in {"audio", "image"}:
            raise ValueError("OTIO media layer kind not supported")
        else:
            layer.properties["duration"] = duration
        project.layers.append(layer)
        project.canvas.duration = max(project.canvas.duration, start + duration)
    # Validate BEFORE touching existing Studio files.
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("Refuse to overwrite an existing Studio project")
    _safe_write(dest, (json.dumps(project.to_dict(), indent=2) + "\n").encode())
    return {
        "format": "otio", "layers": len(project.layers), "output": str(dest),
        "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        "warnings": ["Unmapped FilmCraft advanced interchange is not silently imported"],
    }
