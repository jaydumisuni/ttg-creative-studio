#!/usr/bin/env python3
"""Self-test one-command ad workflow runner."""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for path in (SRC, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from PIL import Image, ImageDraw

from run_ad_workflow import run_workflow
from ttg_project_schema import TTGProject


def make_zip(zip_path: Path) -> None:
    work = zip_path.parent / "zip_source"
    work.mkdir(parents=True, exist_ok=True)
    for index in range(3):
        image = Image.new("RGB", (900, 1280), (20 + index * 40, 10, 50 + index * 30))
        draw = ImageDraw.Draw(image)
        draw.text((120, 160), f"AD ZIP SCENE {index + 1}", fill=(255, 255, 255))
        image.save(work / f"scene_{index + 1}.jpg", quality=90)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(work.rglob("*.jpg")):
            zf.write(path, path.relative_to(work))


def main() -> int:
    work = Path(tempfile.gettempdir()) / "ttg_run_ad_workflow_self_test"
    source_zip = work / "ad.zip"
    output_dir = work / "outputs"
    make_zip(source_zip)
    project_path, contact_sheet, report = run_workflow(source_zip, output_dir, "Runner Self Test Ad")
    project = TTGProject.load(project_path)
    image_layers = [layer for layer in project.layers if layer.type == "image"]
    checks = [
        project_path.exists(),
        contact_sheet.exists(),
        report.exists(),
        project.project_type == "motion",
        len(project.assets) == 3,
        len(image_layers) == 3,
        project.export.get("workflow") == "ad_from_assets",
        "Runner Self Test Ad" in report.read_text(encoding="utf-8"),
    ]
    if not all(checks):
        print("Run ad workflow self-test failed")
        print(checks)
        return 1
    print("Run ad workflow self-test passed")
    print(f"Project: {project_path}")
    print(f"Contact sheet: {contact_sheet}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
