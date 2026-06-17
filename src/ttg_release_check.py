#!/usr/bin/env python3
"""Release readiness checks for TTG Creative Studio."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class ReleaseCheckResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.passed = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class ReleaseChecker:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root)

    def run(self) -> ReleaseCheckResult:
        result = ReleaseCheckResult(passed=True)
        required_paths = [
            "src/ttg_project_schema.py",
            "src/ttg_canvas_engine.py",
            "src/ttg_timeline_engine.py",
            "src/ttg_motion_exporter.py",
            "src/ttg_creative_ui.py",
            "src/ttg_creative_app.py",
            "scripts/launch_creative_studio.py",
            "scripts/validate_repository.py",
            "TTG Creative Studio.spec",
        ]
        for rel in required_paths:
            if not (self.repo_root / rel).exists():
                result.add_error(f"Missing required file: {rel}")
        manifest_dir = self.repo_root / "packs" / "manifests"
        if not manifest_dir.exists():
            result.add_error("Missing packs/manifests directory")
        else:
            manifests = sorted(manifest_dir.glob("*.json"))
            if not manifests:
                result.add_warning("No optional pack manifests found")
            for path in manifests:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if str(data.get("url", "")).startswith("release-url"):
                        result.add_warning(f"Pack manifest uses placeholder URL: {path.name}")
                    for item in data.get("files", []):
                        if str(item.get("url", "")).startswith("release-url"):
                            result.add_warning(f"Pack file uses placeholder URL: {path.name}/{item.get('name')}")
                except Exception as exc:
                    result.add_error(f"Bad manifest {path.name}: {exc}")
        return result
