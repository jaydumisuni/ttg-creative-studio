#!/usr/bin/env python3
"""Launch TTG Creative Studio from a source checkout."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ttg_creative_app import run

def main() -> int:
    # The frozen desktop executable has a bounded, noninteractive smoke path.
    # This checks its bundled Qt/plugins without claiming user GUI acceptance.
    if "--self-check" in sys.argv:
        import json
        from PyQt6.QtWidgets import QApplication
        from ttg_action_engine import ActionEngine
        from ttg_canvas_engine import CanvasRenderer, RenderContext
        app = QApplication.instance() or QApplication([])
        project = ActionEngine().new_project("Frozen Creative Studio Smoke", "image")
        project.canvas.width, project.canvas.height = 48, 48
        actual = CanvasRenderer(RenderContext(ROOT)).render(project)
        print(json.dumps({
            "application": "TTG Creative Studio",
            "packaged_imports": True,
            "renderer_size": list(actual.size),
            "qt": bool(app),
        }))
        return 0
    if "--qualify-gui" in sys.argv:
        import json
        position = sys.argv.index("--qualify-gui")
        if len(sys.argv) != position + 2:
            raise ValueError("--qualify-gui requires one empty proof directory")
        from ttg_frozen_gui_probe import qualify_gui
        proof_dir = Path(sys.argv[position + 1])
        try:
            report = qualify_gui(proof_dir)
        except Exception as exc:
            # Windowed PyInstaller executables otherwise show a modal error
            # popup with no interactive user on CI, hanging Start-Process.
            # Store only a bounded, human-readable error (never raw secrets).
            if proof_dir.is_dir() and not (proof_dir / "gui-proof.json").exists():
                diagnostic = proof_dir / "gui-failure.txt"
                if not diagnostic.exists():
                    diagnostic.write_text(
                        type(exc).__name__ + ": " + str(exc)[:900] + "\n",
                        encoding="utf-8",
                    )
            return 3
        print(json.dumps({"result": report["result"], "checks": len(report["checks"])}))
        return 0
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
