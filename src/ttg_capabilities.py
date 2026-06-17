#!/usr/bin/env python3
"""Capability report for TTG Creative Studio."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json


@dataclass
class CapabilityReport:
    working: list[str] = field(default_factory=list)
    partial: list[str] = field(default_factory=list)
    planned: list[str] = field(default_factory=list)
    blocked: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = ["# TTG Creative Studio Capability Report", ""]
        for title, items in [
            ("Working", self.working),
            ("Partial", self.partial),
            ("Planned", self.planned),
            ("Blocked", self.blocked),
        ]:
            lines.append(f"## {title}")
            lines.append("")
            if items:
                lines.extend([f"- {item}" for item in items])
            else:
                lines.append("- None")
            lines.append("")
        return "\n".join(lines)


def build_capability_report(repo_root: str | Path) -> CapabilityReport:
    repo_root = Path(repo_root)
    report = CapabilityReport()
    required_working = [
        ("Editable .ttgstudio project schema", "src/ttg_project_schema.py"),
        ("Layer/action engine", "src/ttg_action_engine.py"),
        ("2D canvas preview renderer", "src/ttg_canvas_engine.py"),
        ("Timeline/keyframe interpolation", "src/ttg_timeline_engine.py"),
        ("PNG/frame/MP4 export wrapper", "src/ttg_export_service.py"),
        ("Project validation", "src/ttg_validation.py"),
        ("Pack status reader", "src/ttg_pack_status.py"),
        ("Creative Studio PyQt widget", "src/ttg_creative_ui.py"),
        ("Standalone Creative Studio launcher", "scripts/launch_creative_studio.py"),
    ]
    for label, rel in required_working:
        if (repo_root / rel).exists():
            report.working.append(label)
        else:
            report.blocked.append(f"Missing {label}: {rel}")
    if (repo_root / "src/ttg_intro_builder.py").exists():
        report.partial.append("Cinematic intro builder scaffold")
    if (repo_root / "src/ttg_render_plan.py").exists():
        report.partial.append("Render planner with future 3D/audio tasks")
    if (repo_root / "packs" / "manifests").exists():
        report.partial.append("Optional pack manifest system")
    report.planned.extend([
        "True 3D renderer backend",
        "Full layer editing handles on canvas",
        "Advanced timeline UI",
        "Pack downloader with checksum verification in UI",
        "Production-quality cinematic intro render pack",
        "Hunter control API",
    ])
    return report


def save_report(repo_root: str | Path, output_path: str | Path) -> None:
    report = build_capability_report(repo_root)
    path = Path(output_path)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    else:
        path.write_text(report.to_markdown(), encoding="utf-8")
