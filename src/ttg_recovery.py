#!/usr/bin/env python3
"""Crash-safe, limited Creative Studio editable-project recovery snapshots."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

from ttg_project_schema import TTGProject


def user_data_root() -> Path:
    if sys.platform == "win32":
        return Path(os.getenv("LOCALAPPDATA") or Path.home()/"AppData"/"Local") / "TTG Creative Studio"
    return Path(os.getenv("XDG_DATA_HOME") or Path.home()/".local"/"share") / "ttg-creative-studio"


class RecoveryStore:
    def __init__(self, root: Path | None = None, limit: int = 15) -> None:
        if not (1 <= limit <= 100):
            raise ValueError("Recovery limit must be 1–100")
        self.root = (root or user_data_root()/"recovery").resolve()
        self.limit = limit

    def _key(self, project_path: Path | None, identity: str = "unsaved") -> str:
        key = str(project_path.resolve()) if project_path else identity
        return hashlib.sha256(key.encode()).hexdigest()

    def path_for(self, project_path: Path | None, identity: str = "unsaved") -> Path:
        return self.root/(self._key(project_path, identity) + ".json")

    def snapshot(self, project: TTGProject, project_path: Path | None,
                 identity: str = "unsaved") -> Path:
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        source = str(project_path.resolve()) if project_path else ""
        body = json.dumps({
            "format": "ttg.creative.recovery.v1",
            "source": source,
            "project": project.to_dict(),
        }, ensure_ascii=False)
        if len(body) > 25_000_000:
            raise ValueError("Recovery snapshot exceeds 25MB")
        final = self.path_for(project_path, identity)
        fd, name = tempfile.mkstemp(prefix=".ttg-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(name, final)
            # A directory sync is available on POSIX; Windows replace is atomic.
            if os.name == "posix":
                descriptor = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            self.prune()
            return final
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def load(self, snapshot: Path) -> tuple[TTGProject, Path | None]:
        source = snapshot.resolve()
        if source.parent != self.root or source.suffix != ".json":
            raise ValueError("Recovery snapshot must come from the recovery directory")
        if source.stat().st_size > 25_000_000:
            raise ValueError("Oversized recovery file")
        payload = json.loads(source.read_text(encoding="utf-8"))
        if payload.get("format") != "ttg.creative.recovery.v1":
            raise ValueError("Invalid recovery format")
        # Reuse canonical Studio deserializer without modifying the original.
        raw = self.root/(".reading-" + source.stem + ".tmp")
        try:
            raw.write_text(json.dumps(payload["project"]), encoding="utf-8")
            project = TTGProject.load(raw)
        finally:
            raw.unlink(missing_ok=True)
        path = Path(payload["source"]) if payload.get("source") else None
        return project, path

    def pending(self) -> list[Path]:
        if not self.root.exists():
            return []
        return sorted(self.root.glob("*.json"), key=lambda p:p.stat().st_mtime, reverse=True)

    def clear(self, project_path: Path | None, identity: str = "unsaved") -> None:
        self.path_for(project_path, identity).unlink(missing_ok=True)

    def prune(self) -> None:
        for path in self.pending()[self.limit:]:
            path.unlink(missing_ok=True)
