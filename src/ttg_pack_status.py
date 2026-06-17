#!/usr/bin/env python3
"""Pack status helpers for TTG Creative Studio."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class PackStatus:
    id: str
    name: str
    installed: bool
    required: bool
    kind: str
    description: str


class PackStatusReader:
    def __init__(self, repo_root: str | Path, app_data_dir: str | Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.manifest_dir = self.repo_root / "packs" / "manifests"
        self.app_data_dir = Path(app_data_dir) if app_data_dir else Path.home() / "AppData" / "Local" / "TheTechGuyCreativeStudio"
        self.installed_manifest_dir = self.app_data_dir / "manifests"

    def list_statuses(self) -> list[PackStatus]:
        statuses: list[PackStatus] = []
        if not self.manifest_dir.exists():
            return statuses
        for path in sorted(self.manifest_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            pack_id = str(data.get("id", path.stem))
            installed = (self.installed_manifest_dir / f"{pack_id}.json").exists()
            statuses.append(PackStatus(
                id=pack_id,
                name=str(data.get("name", pack_id)),
                installed=installed,
                required=bool(data.get("required", False)),
                kind=str(data.get("kind", "asset")),
                description=str(data.get("description", "")),
            ))
        return statuses
