#!/usr/bin/env python3
"""Print the active THETECHGUY Building Standard gates for CI logs."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDARD = ROOT / "docs" / "THETECHGUY_BUILDING_STANDARD.md"
REQUIRED_PHRASES = [
    "Finish, then prove",
    "Code should justify execution",
    "Claims must match implementation",
    "Evidence before conclusions",
    "Tests are proof, not discovery",
    "Visual verification is mandatory for visual work",
    "Engine first, UI last",
    "Editable output first",
    "Hunter coordinates, workers execute",
]


def main() -> int:
    if not STANDARD.exists():
        print(f"Missing building standard: {STANDARD}")
        return 1
    text = STANDARD.read_text(encoding="utf-8")
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase not in text]
    print("THETECHGUY Building Standard")
    print("============================")
    for phrase in REQUIRED_PHRASES:
        print(f"- {phrase}")
    if missing:
        print("Missing required standard phrases:")
        for phrase in missing:
            print(f"  - {phrase}")
        return 1
    print("Building standard is present and complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
