#!/usr/bin/env python3
"""Create a simple failure report when proof generation cannot complete."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
REPORT = OUT / "FAILURE_REPORT.md"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    lines = [
        "# TTG Visual Proof Failure Report",
        "",
        "The visual proof workflow did not complete successfully.",
        "",
        f"Generated at UTC: {datetime.now(timezone.utc).isoformat()}",
        f"GitHub SHA: {os.environ.get('GITHUB_SHA', 'unknown')}",
        f"GitHub workflow: {os.environ.get('GITHUB_WORKFLOW', 'unknown')}",
        f"GitHub run id: {os.environ.get('GITHUB_RUN_ID', 'unknown')}",
        "",
        "Check the Actions log step that failed. This report exists so the artifact package still has a readable status file.",
        "",
        "Release remains blocked.",
        "Video proof remains blocked until visual proof artifacts are generated and reviewed.",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved failure report: {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
