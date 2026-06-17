#!/usr/bin/env python3
"""Background remover integration adapter for Creative Studio."""

from __future__ import annotations

from pathlib import Path
from typing import Callable


class BackgroundRemovalTool:
    """Wrap existing bg_core background remover functions as a Creative Studio tool."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)

    def available(self) -> bool:
        try:
            import bg_core  # noqa: F401
            return True
        except Exception:
            return False

    def remove_background(self, input_path: str | Path, output_dir: str | Path, status: Callable[[str], None] | None = None) -> Path:
        if not self.available():
            raise RuntimeError("Background removal engine is not available.")
        from bg_core import build_trim_plan, run_local_processing

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        plan = build_trim_plan("remove background")
        result = Path(run_local_processing(str(input_path), plan, status or (lambda _: None)))
        target = output_dir / f"{Path(input_path).stem}_cutout.png"
        if result != target:
            target.write_bytes(result.read_bytes())
        return target
