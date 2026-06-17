#!/usr/bin/env python3
"""Verify release-track implementation coverage for TTG Creative Studio."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

MODULES = [
    "ttg_interactive_canvas",
    "ttg_properties_panel",
    "ttg_timeline_panel",
    "ttg_text_renderer",
    "ttg_cinematic_renderer",
    "ttg_ffmpeg_manager",
    "ttg_pack_downloader",
    "ttg_background_tool",
    "ttg_creative_workspace",
]

FILES = [
    "scripts/build_creative_studio.cmd",
    "TTG Creative Studio.spec",
    "installer/creative_studio_core.iss",
    "packs/manifests/video-export.json",
]


def main() -> int:
    errors = []
    for module in MODULES:
        try:
            importlib.import_module(module)
        except Exception as exc:
            errors.append(f"module {module}: {exc}")
    for rel in FILES:
        if not (ROOT / rel).exists():
            errors.append(f"missing {rel}")
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print("TTG Creative Studio release-track verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
