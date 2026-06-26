#!/usr/bin/env python3
"""Self-test Creative Studio ad workflow from generated folder and ZIP assets.

This proves the engine/workflow can create an editable ad project and visual
proof output before UI polish.
"""

from __future__ import annotations

import os
import shutil
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

from build_ad_project_from_assets import build_ad_project
from render_ad_project_contact_sheet import render_contact_sheet
from ttg_project_schema import TTGProject


def make_sample_assets(asset_dir: Path, count: int = 4) -> None:
    if asset_dir.exists():
        shutil.rmtree(asset_dir)
    asset_dir.mkdir(parents=True, exist_ok=True)
    for index in range(count):
        image = Image.new("RGB", (900, 1280), (8 + index * 20, 12, 34 + index * 30))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((80, 120, 820, 1160), radius=60, outline=(0, 229, 255), width=10)
        draw.text((130, 180), f"TTG EVENT SCENE {index + 1}", fill=(255, 255, 255))
        draw.text((130, 260), "Invite • Guests • QR • Share", fill=(188, 19, 254))
        image.save(asset_dir / f"scene_{index + 1:02d}.jpg", quality=92)


def make_zip(asset_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(asset_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(asset_dir))


def publish_artifacts(project_path: Path, contact_sheet: Path, zip_project_path: Path) -> None:
    artifact_dir = Path(os.environ.get("TTG_AD_WORKFLOW_ARTIFACT_DIR", ROOT / "outputs" / "ad_workflow"))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(project_path, artifact_dir / project_path.name)
    shutil.copy2(zip_project_path, artifact_dir / zip_project_path.name)
    shutil.copy2(contact_sheet, artifact_dir / contact_sheet.name)
    report = artifact_dir / "AD_WORKFLOW_PROOF.md"
    report.write_text(
        "# TTG Ad Workflow Proof\n\n"
        "This artifact proves the engine/workflow path before UI polish.\n\n"
        f"- Folder project: `{project_path.name}`\n"
        f"- ZIP project: `{zip_project_path.name}`\n"
        f"- Contact sheet: `{contact_sheet.name}`\n\n"
        "Pipeline: folder/ZIP assets → editable `.ttgstudio.json` project → visual contact sheet proof.\n",
        encoding="utf-8",
    )


def validate_project(project_path: Path, expected_assets: int = 4) -> tuple[TTGProject, list[bool]]:
    loaded = TTGProject.load(project_path)
    image_layers = [layer for layer in loaded.layers if layer.type == "image"]
    checks = [
        project_path.exists(),
        loaded.project_type == "motion",
        loaded.canvas.width == 1080,
        loaded.canvas.height == 1920,
        loaded.canvas.fps == 30,
        loaded.export.get("workflow") == "ad_from_assets",
        loaded.export.get("creative_studio_test", {}).get("normalized_images") == expected_assets,
        len(loaded.assets) == expected_assets,
        len(image_layers) == expected_assets,
        all(layer.keyframes for layer in image_layers),
        any(layer.name == "Ad Title" for layer in loaded.layers),
        any(layer.name == "Call To Action" for layer in loaded.layers),
        len(loaded.audio_markers) >= 2,
    ]
    return loaded, checks


def main() -> int:
    work = Path(tempfile.gettempdir()) / "ttg_ad_project_workflow_self_test"
    asset_dir = work / "assets"
    zip_path = work / "ad_assets.zip"
    folder_output = work / "ttg_ad_from_folder.ttgstudio.json"
    zip_output = work / "ttg_ad_from_zip.ttgstudio.json"
    contact_sheet = work / "ttg_ad_contact_sheet.jpg"
    make_sample_assets(asset_dir)
    make_zip(asset_dir, zip_path)

    folder_project = build_ad_project(asset_dir, folder_output, "Workflow Folder Self Test Ad")
    zip_project = build_ad_project(zip_path, zip_output, "Workflow ZIP Self Test Ad", workspace=work / "zip_import_workspace")
    rendered = render_contact_sheet(zip_output, contact_sheet)
    loaded_folder, folder_checks = validate_project(folder_output)
    loaded_zip, zip_checks = validate_project(zip_output)
    publish_artifacts(folder_output, rendered, zip_output)

    with Image.open(rendered) as proof:
        proof_size = proof.size
    checks = [
        rendered.exists(),
        proof_size[0] >= 800,
        proof_size[1] >= 600,
        folder_project.canvas.duration == loaded_folder.canvas.duration,
        zip_project.canvas.duration == loaded_zip.canvas.duration,
        *folder_checks,
        *zip_checks,
    ]
    if not all(checks):
        print("Ad project workflow self-test failed")
        print(checks)
        print(f"Folder project: {folder_output}")
        print(f"ZIP project: {zip_output}")
        print(f"Contact sheet: {rendered}")
        return 1
    print("Ad project workflow self-test passed")
    print(f"Folder project: {folder_output}")
    print(f"ZIP project: {zip_output}")
    print(f"Contact sheet: {rendered} {proof_size}")
    print(f"Folder assets: {len(loaded_folder.assets)} ZIP assets: {len(loaded_zip.assets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
