#!/usr/bin/env python3
"""
Download the rembg models used by the installer into the local models folder.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path


MODELS = {
    "isnet-general-use.onnx": {
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx",
        "md5": "fc16ebd8b0c10d971d3513d564d01e29",
    },
    "u2net_human_seg.onnx": {
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net_human_seg.onnx",
        "md5": "c09ddc2e0104f800e3e1bb4652583d1f",
    },
    "isnet-anime.onnx": {
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-anime.onnx",
        "md5": "6f184e756bb3bd901c8849220a83e38e",
    },
    "u2netp.onnx": {
        "url": "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx",
        "md5": "8e83ca70e441ab06c318d82300c84806",
    },
}


def md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(url: str, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".part")
    if temporary.exists():
        temporary.unlink()

    with urllib.request.urlopen(url) as response, temporary.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)

    temporary.replace(destination)


def ensure_model(model_dir: Path, filename: str, meta: dict[str, str]) -> None:
    destination = model_dir / filename
    if destination.exists() and md5_file(destination) == meta["md5"]:
        print(f"Ready: {filename}")
        return

    if destination.exists():
        destination.unlink()

    print(f"Downloading: {filename}")
    download_file(meta["url"], destination)

    if md5_file(destination) != meta["md5"]:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum mismatch for {filename}")

    print(f"Saved: {destination}")


def main() -> int:
    project_root = Path(__file__).resolve().parent
    model_dir = project_root / "models"
    model_dir.mkdir(parents=True, exist_ok=True)

    for filename, meta in MODELS.items():
        ensure_model(model_dir, filename, meta)

    print(f"Models ready in {model_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
