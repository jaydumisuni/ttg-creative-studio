#!/usr/bin/env python3
"""Self-test asset package importer for folder and ZIP sources."""

from __future__ import annotations

import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PIL import Image

from ttg_asset_package import import_asset_package


def make_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (320, 480), color).save(path, quality=90)


def main() -> int:
    work = Path(tempfile.gettempdir()) / "ttg_asset_package_self_test"
    source_dir = work / "source"
    zip_path = work / "sample_assets.zip"
    make_image(source_dir / "scene_01.jpg", (10, 20, 40))
    make_image(source_dir / "nested" / "scene_02.png", (40, 20, 80))
    (source_dir / "ignore.txt").write_text("ignore me", encoding="utf-8")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in source_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source_dir))

    folder_import = import_asset_package(source_dir, work / "folder_workspace")
    zip_import = import_asset_package(zip_path, work / "zip_workspace")

    checks = [
        len(folder_import.image_files) == 2,
        len(zip_import.image_files) == 2,
        all(path.exists() for path in folder_import.image_files),
        all(path.exists() for path in zip_import.image_files),
        not any(path.name == "ignore.txt" for path in folder_import.files),
        not any(path.name == "ignore.txt" for path in zip_import.files),
        folder_import.has_images,
        zip_import.has_images,
    ]
    if not all(checks):
        print("Asset package self-test failed")
        print(checks)
        return 1
    print("Asset package self-test passed")
    print(f"Folder import images: {len(folder_import.image_files)}")
    print(f"ZIP import images: {len(zip_import.image_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
