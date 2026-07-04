#!/usr/bin/env python3
"""Asset package ingestion for TTG Creative Studio.

Engine-level support for folders and ZIPs. UI can call this later, but the
workflow should be testable without UI first.
"""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".ogg"}
SUPPORTED_EXTS = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS


@dataclass(frozen=True)
class ImportedAssetPackage:
    source: str
    workspace: Path
    files: tuple[Path, ...]
    image_files: tuple[Path, ...]
    video_files: tuple[Path, ...]
    audio_files: tuple[Path, ...]

    @property
    def has_images(self) -> bool:
        return bool(self.image_files)


def _safe_member_path(base: Path, member_name: str) -> Path:
    target = (base / member_name).resolve()
    base_resolved = base.resolve()
    try:
        target.relative_to(base_resolved)
    except ValueError as exc:
        raise ValueError(f"Unsafe ZIP member path: {member_name}") from exc
    return target


def _copy_supported_files(source_dir: Path, workspace: Path) -> list[Path]:
    imported: list[Path] = []
    for src in sorted(source_dir.rglob("*")):
        if not src.is_file() or src.suffix.lower() not in SUPPORTED_EXTS:
            continue
        rel = src.relative_to(source_dir)
        dst = workspace / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        imported.append(dst)
    return imported


def import_asset_package(source: Path, workspace: Path) -> ImportedAssetPackage:
    source = source.expanduser().resolve()
    workspace = workspace.expanduser().resolve()
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    if source.is_dir():
        files = _copy_supported_files(source, workspace)
    elif source.is_file() and source.suffix.lower() == ".zip":
        extract_dir = workspace / "_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                if Path(member.filename).suffix.lower() not in SUPPORTED_EXTS:
                    continue
                target = _safe_member_path(extract_dir, member.filename)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(member) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
        files = _copy_supported_files(extract_dir, workspace / "assets")
    else:
        raise ValueError(f"Unsupported asset package source: {source}")

    image_files = tuple(path for path in files if path.suffix.lower() in IMAGE_EXTS)
    video_files = tuple(path for path in files if path.suffix.lower() in VIDEO_EXTS)
    audio_files = tuple(path for path in files if path.suffix.lower() in AUDIO_EXTS)
    return ImportedAssetPackage(
        source=str(source),
        workspace=workspace,
        files=tuple(files),
        image_files=image_files,
        video_files=video_files,
        audio_files=audio_files,
    )
