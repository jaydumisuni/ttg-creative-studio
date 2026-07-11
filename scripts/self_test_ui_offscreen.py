#!/usr/bin/env python3
"""Offscreen UI smoke test for TTG Creative Studio.

This creates QApplication + CreativeStudioWindow using Qt offscreen mode,
verifies the central workspace exists, and proves the app-facing ad workflow can
load an editable project from a ZIP without requiring a visible desktop.
"""

from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PIL import Image, ImageDraw


def make_ad_zip(zip_path: Path) -> None:
    source = zip_path.parent / "ui_ad_source"
    source.mkdir(parents=True, exist_ok=True)
    for index in range(2):
        image = Image.new("RGB", (720, 1080), (12 + index * 50, 15, 55 + index * 20))
        draw = ImageDraw.Draw(image)
        draw.text((80, 100), f"UI AD SCENE {index + 1}", fill=(255, 255, 255))
        image.save(source / f"scene_{index + 1}.jpg", quality=90)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(source.rglob("*.jpg")):
            zf.write(path, path.relative_to(source))


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    from ttg_creative_app import CreativeStudioWindow

    app = QApplication.instance() or QApplication([])
    window = CreativeStudioWindow()
    workspace = window.centralWidget()
    work = Path(tempfile.gettempdir()) / "ttg_ui_offscreen_ad_workflow"
    work.mkdir(parents=True, exist_ok=True)
    zip_path = work / "ad.zip"
    make_ad_zip(zip_path)
    if workspace is not None and hasattr(workspace, "import_ad_source"):
        workspace.import_ad_source(zip_path)
    checks = [
        window.windowTitle() == "TTG Creative Studio",
        workspace is not None,
        hasattr(workspace, "advanced"),
        hasattr(workspace, "canvas"),
        hasattr(workspace, "properties"),
        hasattr(workspace, "preset_actions"),
        hasattr(workspace, "import_ad_zip"),
        hasattr(workspace, "import_ad_folder"),
        hasattr(workspace, "import_ad_source"),
        getattr(workspace, "project", None) is not None,
        len(getattr(workspace.project, "assets", [])) == 2,
        len([layer for layer in workspace.project.layers if layer.type == "image"]) == 2,
        workspace.project_path is not None,
    ]
    window.close()
    app.processEvents()
    if not all(checks):
        print("Offscreen UI smoke test failed")
        print(checks)
        return 1
    print("Offscreen UI smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
