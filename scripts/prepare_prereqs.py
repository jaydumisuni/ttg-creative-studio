#!/usr/bin/env python3
"""
Download installer prerequisites into the local prereqs folder.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path


PREREQUISITES = {
    "vc_redist.x64.exe": {
        "url": "https://aka.ms/vc14/vc_redist.x64.exe",
        "min_size": 5 * 1024 * 1024,
    },
}


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


def ensure_prerequisite(target_dir: Path, filename: str, meta: dict[str, object]) -> None:
    destination = target_dir / filename
    min_size = int(meta["min_size"])
    url = str(meta["url"])

    if destination.exists() and destination.stat().st_size >= min_size:
        print(f"Ready: {filename}")
        return

    destination.unlink(missing_ok=True)
    print(f"Downloading: {filename}")
    download_file(url, destination)

    if destination.stat().st_size < min_size:
        destination.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded prerequisite is too small: {filename}")

    print(f"Saved: {destination}")


def main() -> int:
    project_root = Path(__file__).resolve().parent
    prereq_dir = project_root / "prereqs"
    prereq_dir.mkdir(parents=True, exist_ok=True)

    for filename, meta in PREREQUISITES.items():
        ensure_prerequisite(prereq_dir, filename, meta)

    print(f"Prerequisites ready in {prereq_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
