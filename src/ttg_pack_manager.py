#!/usr/bin/env python3
"""
On-demand pack manager for TTG Creative Studio.

The app installer should stay small. Heavy models, templates, 3D packs,
sounds, and AI helpers are downloaded only when a feature needs them.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal
import hashlib
import json
import urllib.request

PackKind = Literal["model", "template", "motion", "schematic", "sound", "brand", "ai", "font", "asset"]


@dataclass
class PackFile:
    name: str
    url: str
    path: str
    size_mb: float | None = None
    sha256: str | None = None


@dataclass
class PackManifest:
    id: str
    name: str
    version: str
    kind: PackKind
    required: bool = False
    description: str = ""
    files: list[PackFile] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "PackManifest":
        return PackManifest(
            id=data["id"],
            name=data["name"],
            version=data.get("version", "0.1.0"),
            kind=data.get("kind", "asset"),
            required=data.get("required", False),
            description=data.get("description", ""),
            files=[PackFile(**f) for f in data.get("files", [])],
        )


class PackManager:
    def __init__(self, app_data_dir: str | Path):
        self.app_data_dir = Path(app_data_dir)
        self.packs_dir = self.app_data_dir / "packs"
        self.manifests_dir = self.app_data_dir / "manifests"
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        self.manifests_dir.mkdir(parents=True, exist_ok=True)

    def installed_manifest_path(self, pack_id: str) -> Path:
        return self.manifests_dir / f"{pack_id}.json"

    def is_installed(self, pack_id: str) -> bool:
        return self.installed_manifest_path(pack_id).exists()

    def save_manifest(self, manifest: PackManifest) -> None:
        self.installed_manifest_path(manifest.id).write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )

    def load_manifest(self, pack_id: str) -> PackManifest:
        data = json.loads(self.installed_manifest_path(pack_id).read_text(encoding="utf-8"))
        return PackManifest.from_dict(data)

    def verify_file(self, file_path: str | Path, expected_sha256: str | None) -> bool:
        if not expected_sha256:
            return True
        h = hashlib.sha256()
        with Path(file_path).open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest().lower() == expected_sha256.lower()

    def download_pack(self, manifest: PackManifest, progress=None) -> None:
        """Download a pack's files into the local packs directory.

        progress callback signature: progress(message: str)
        """
        pack_root = self.packs_dir / manifest.id
        pack_root.mkdir(parents=True, exist_ok=True)
        for item in manifest.files:
            target = pack_root / item.path
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and self.verify_file(target, item.sha256):
                if progress:
                    progress(f"Already installed: {item.name}")
                continue
            if progress:
                progress(f"Downloading {item.name}...")
            urllib.request.urlretrieve(item.url, target)
            if not self.verify_file(target, item.sha256):
                target.unlink(missing_ok=True)
                raise RuntimeError(f"Downloaded file failed checksum: {item.name}")
        self.save_manifest(manifest)

    def require_pack(self, manifest: PackManifest, progress=None) -> bool:
        """Return True if installed; otherwise download it and return True.

        UI can wrap this with a confirmation dialog before calling.
        """
        if self.is_installed(manifest.id):
            return True
        self.download_pack(manifest, progress=progress)
        return True
