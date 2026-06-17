#!/usr/bin/env python3
"""Pack download/install service for TTG Creative Studio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import urllib.request


@dataclass
class DownloadResult:
    pack_id: str
    installed_files: int
    skipped_files: int


class PackDownloader:
    def __init__(self, repo_root: str | Path, app_data_dir: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.manifest_dir = self.repo_root / "packs" / "manifests"
        self.app_data_dir = Path(app_data_dir) if app_data_dir else Path.home() / "AppData" / "Local" / "TheTechGuyCreativeStudio"
        self.packs_dir = self.app_data_dir / "packs"
        self.installed_dir = self.app_data_dir / "manifests"
        self.packs_dir.mkdir(parents=True, exist_ok=True)
        self.installed_dir.mkdir(parents=True, exist_ok=True)

    def load_manifest(self, pack_id: str) -> dict:
        path = self.manifest_dir / f"{pack_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing pack manifest: {pack_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def verify(self, path: Path, expected: str | None) -> bool:
        if not expected or expected in {"replace-later", ""}:
            return True
        return self.sha256(path).lower() == expected.lower()

    def install_pack(self, pack_id: str, progress=None) -> DownloadResult:
        manifest = self.load_manifest(pack_id)
        installed = 0
        skipped = 0
        for file_info in manifest.get("files", []):
            url = str(file_info.get("url", ""))
            if not url or url.startswith("release-url"):
                raise RuntimeError(f"Pack {pack_id} has no real download URL for {file_info.get('name')}")
            target = self.packs_dir / pack_id / str(file_info.get("path", file_info.get("name", "file.bin")))
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and self.verify(target, file_info.get("sha256")):
                skipped += 1
                continue
            if progress:
                progress(f"Downloading {file_info.get('name', target.name)}")
            urllib.request.urlretrieve(url, target)
            if not self.verify(target, file_info.get("sha256")):
                target.unlink(missing_ok=True)
                raise RuntimeError(f"Checksum failed for {target.name}")
            installed += 1
        (self.installed_dir / f"{pack_id}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return DownloadResult(pack_id, installed, skipped)
