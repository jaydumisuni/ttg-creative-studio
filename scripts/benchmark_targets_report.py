#!/usr/bin/env python3
"""Report benchmark targets for TTG Creative Studio."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "BENCHMARK_TARGETS.md"
REQUIRED = [
    "Penpot",
    "tldraw",
    "Excalidraw",
    "CreatiPoster",
    "OpenShot",
    "Flowblade",
    "Olive",
    "Remotion",
    "Motion Canvas",
    "Blender",
    "Visual proof artifact",
    "Next implementation target",
]


def main() -> int:
    if not DOC.exists():
        print("Missing benchmark targets doc")
        return 1
    text = DOC.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED if item not in text]
    print("TTG benchmark targets")
    print("=====================")
    for item in REQUIRED:
        print(f"- {item}")
    if missing:
        print("Missing benchmark markers:")
        for item in missing:
            print(f"  - {item}")
        return 1
    print("Benchmark target strategy is present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
