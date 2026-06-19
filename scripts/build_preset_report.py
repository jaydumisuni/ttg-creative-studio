#!/usr/bin/env python3
"""Build a readable Advanced Mode preset report."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "outputs"
REPORT = OUT / "ADVANCED_PRESET_REPORT.md"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_advanced_presets import presets_by_group


def main() -> int:
    lines = [
        "# Advanced Mode Preset Report",
        "",
        "These presets define the professional controls that must be exposed through Advanced Mode.",
        "",
    ]
    for group, presets in presets_by_group().items():
        lines.append(f"## {group}")
        lines.append("")
        for preset in presets:
            lines.append(f"- **{preset.name}** (`{preset.id}`): {preset.description}")
        lines.append("")
    lines.extend([
        "## Gate",
        "",
        "The hidden proof renderer is not enough. These presets must become visible/editable in the app UI before release.",
    ])
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved preset report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
